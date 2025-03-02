import express, { Request, Response } from "express";
import { createGraph } from "./ai/graph";
import { HumanMessage } from "@langchain/core/messages";
import multer from "multer";
import fs from "fs";
import { storeDocument, queryDocuments } from "./ai/rag";

if (!fs.existsSync("uploads")) {
  fs.mkdirSync("uploads");
}
const app = express();
const port: number = 3008;

// Add middleware for JSON parsing and static files
app.use(express.json());
app.use(express.static("public"));

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "uploads/");
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  },
});

const upload = multer({
  storage,
  fileFilter: (req, file, cb) => {
    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error("Invalid file type. Only PDF and DOCX are allowed."));
    }
  },
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB
  },
});

// File upload endpoint
app.post(
  "/upload",
  upload.single("document"),
  async (req: Request, res: Response) => {
    try {
      const { collectionName } = req.body;
      if (!req.file || !collectionName) {
        res.status(400).json({ error: "No file uploaded" });
        return;
      }

      const filePath = req.file!.path;
      const fileExtension = req.file!.mimetype.split("/")[1];
      // Process the document and store in Qdrant
      const docId = await storeDocument(
        req.file.buffer,
        filePath,
        collectionName,
        fileExtension
      );

      res.status(200).json({
        message: "Document processed successfully",
        documentId: docId,
        filename: req.file!.originalname,
      });
    } catch (error) {
      console.error("Error processing document:", error);
      res.status(500).json({ error: "Failed to process document" });
    }
  }
);

// Query endpoint
app.post("/query", async (req: Request, res: Response) => {
  try {
    const { query, collectionName } = req.body;

    if (!query || !collectionName) {
      res.status(400).json({ error: "Query and collection name are required" });
      return;
    }
    const results = await queryDocuments(query, collectionName, 3);

    res.status(200).json({ results });
  } catch (error) {
    console.error("Error querying documents:", error);
    res.status(500).json({ error: "Failed to query documents" });
  }
});

// the chat endpoint
app.post("/chat/", async (req: Request, res: Response) => {
  try {
    const { message } = req.body;
    console.log("Message:", message);
    const inputMessage = new HumanMessage({ content: message });
    const config = {
      configurable: { thread_id: "2" },
      recursionLimit: 100,
      streamMode: "values" as const,
    };

    const coreAgentGraph = await createGraph();

    const streamResults = await coreAgentGraph.invoke(
      { messages: [inputMessage] },
      config
    );

    let finalResponse =
      streamResults.messages[streamResults.messages.length - 1];
    // for await (const output of streamResults) {
    //   // console.log("Streaming Output::",output)
    //     if (!output?.__end__ && output.messages) {
    //         const lastMessage = output.messages[output.messages.length - 1];
    //         finalResponse = lastMessage.content;
    //     }
    // }

    console.log("Final Response::", finalResponse);
    res.json({ response: finalResponse.content });
  } catch (error) {
    console.error("Error processing request:", error);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});

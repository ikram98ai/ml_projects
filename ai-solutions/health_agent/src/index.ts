/**
 * Sets up an Express server with endpoints for file upload and chat processing.
 *
 * - The server listens on port 3008.
 * - Middleware is added for JSON parsing and serving static files.
 * - Multer is configured for handling file uploads with specific file type and size restrictions.
 *
 * Endpoints:
 *
 * - POST /upload
 *   - Uploads a document, processes it, and stores it in a vector database.
 *   - Request body should contain a file (PDF or DOCX) and a collection name.
 *   - Responds with a success message and the number of chunks stored.
 *
 * - POST /chat/
 *   - Processes a chat message and generates a response using a core agent graph.
 *   - Request body should contain a message.
 *   - Responds with the generated response content.
 *
 * Error Handling:
 * - Returns appropriate error messages and status codes for various error scenarios.
 *
 * @module Server
 */
import express, { Request, Response } from "express";
import { createGraph } from "./ai/graph";
import { HumanMessage } from "@langchain/core/messages";
import multer from "multer";
import fs from "fs";
import { processDocument, storeDocument } from "./ai/rag";
import { toolEmitter, ToolExecution } from "./ai/tools";

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

// File upload, preocessed and store in vector database endpoint
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

      const filePath = req.file.path;
      const mimetype = req.file.mimetype;

      // Process the document and store in Qdrant
      const chunks = await processDocument(filePath, mimetype);
      const chunk_len = await storeDocument(chunks, collectionName);

      res.status(200).json({
        message: `Document stored successfully with chunks ${chunk_len}`,
      });
    } catch (error) {
      console.error("Error processing document:", error);
      res.status(500).json({ error: "Failed to process document" });
    }
  }
);

// the chat endpoint
app.post("/chat/", async (req: Request, res: Response) => {
  try {
    const { message } = req.body;
    const toolCalls: ToolExecution[] = [];

    const toolCallListener = (toolCall: ToolExecution) => {
      toolCalls.push(toolCall);
    };
    toolEmitter.on("tool-call", toolCallListener);

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
    let finalResponse = streamResults.messages[streamResults.messages.length - 1];

    toolEmitter.off("tool-call", toolCallListener);

    res.json({ response: finalResponse.content, tool_calls: toolCalls });
  } catch (error) {
    console.error("Error processing request:", error);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});

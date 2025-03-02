// import { QdrantClient } from "@qdrant/js-client-rest";
import { QdrantVectorStore } from "@langchain/qdrant";
import { GoogleGenerativeAIEmbeddings } from "@langchain/google-genai";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { DocxLoader } from "@langchain/community/document_loaders/fs/docx";
import { v4 as uuidv4 } from "uuid";
import { Document } from "@langchain/core/documents";
import dotenv from 'dotenv';
dotenv.config();

// Create vector store instance
const embeddings = new GoogleGenerativeAIEmbeddings({
  model: "models/text-embedding-004",
  apiKey: process.env.GEMINI_API_KEY,
});

export async function queryDocuments(
  query: string,
  collectionName: string = "documents",
  k = 3
) {
  const vectorStore = await QdrantVectorStore.fromExistingCollection(
    embeddings,
    {
      url: process.env.QDRANT_URL,
      apiKey: process.env.QDRANT_API_KEY,
      collectionName: collectionName,
    }
  );
  return vectorStore.similaritySearch(query, k);
}

// Universal document processor
export async function processDocument(
  filePath: string,
  mimeType: string
) {
  try {
    console.log("Processing document:", mimeType, filePath);
    
    // Validate input
    if (!filePath || !mimeType) {
      throw new Error("Missing required parameters");
    }

    // Load document based on type
    let content: string;
 
    if (mimeType === "application/pdf") {
      const pdfLoader = new PDFLoader(filePath);
      const pdfDocs = await pdfLoader.load();
      content = pdfDocs.map((d) => d.pageContent).join("\n");
    } else if (
      mimeType ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ) {
      const docsLoader = new DocxLoader(filePath);
      const wordDocs = await docsLoader.load();
      content = wordDocs.map((d) => d.pageContent).join("\n");
    } else {
      throw new Error(`Unsupported file type: ${mimeType}`);
    }


    // Validate extracted content
    if (!content || content.trim().length === 0) {
      throw new Error("No readable content found in document");
    }

    // Split document into chunks
    const splitter = new RecursiveCharacterTextSplitter({
      chunkSize: 1000,
      chunkOverlap: 200,
    });

    const docId = uuidv4(); // Generate unique ID per document
    const chunks = await splitter.createDocuments(
      [content],
      [{ source: filePath, docId }],
      {
        chunkHeader: `SOURCE: ${filePath}\n\n`, // Add header for context
      }
    );

    return chunks;
  } catch (error) {
    console.error("Document processing failed:", error);
    throw new Error(`Document processing failed: ${(error as Error).message}`);
  }
}

export async function storeDocument(
  chunks: Document<Record<string, any>>[],
  collectionName: string
) {

  console.log("qdrant url::", process.env.QDRANT_URL);

  const vectorStore = await QdrantVectorStore.fromDocuments(
    chunks,
    embeddings,
    {
      url: process.env.QDRANT_URL,
      collectionName: collectionName,
      collectionConfig: {
        vectors: {
          size: 768, // For text-embedding-004
          distance: "Cosine",
        },
      },
    }
  );

  return chunks.length;
}

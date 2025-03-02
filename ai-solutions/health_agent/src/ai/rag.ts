// import { QdrantClient } from "@qdrant/js-client-rest";
import { QdrantVectorStore } from "@langchain/qdrant";
import { GoogleGenerativeAIEmbeddings } from "@langchain/google-genai";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { DocxLoader } from "@langchain/community/document_loaders/fs/docx";
import { v4 as uuidv4 } from "uuid";

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
export async function storeDocument(
  file: Buffer,
  fileName: string,
  collectionName: string,
  mimeType: string
) {
  // Load document based on type
  console.log("Processing document:", mimeType, fileName);
  let content: string;
  if (mimeType === "application/pdf") {
    const pdfLoader = new PDFLoader(new Blob([file]));
    const pdfDocs = await pdfLoader.load();
    content = pdfDocs.map((d) => d.pageContent).join("\n");
  } else if (
    mimeType ===
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ) {
    const docsLoader = new DocxLoader(new Blob([file]));
    const wordDocs = await docsLoader.load();
    content = wordDocs.map((d) => d.pageContent).join("\n");
  } else {
    throw new Error("Unsupported file type");
  }

  // Split document into chunks
  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 1000,
    chunkOverlap: 200,
  });

  const chunks = await splitter.createDocuments(
    [content],
    [
      {
        source: fileName,
        docId: uuidv4(),
      },
    ]
  );

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

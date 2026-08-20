import { DynamicStructuredTool } from "@langchain/core/tools";
import { z } from "zod";
import { queryDocuments } from "./rag";
import { EventEmitter } from "events";

export const toolEmitter = new EventEmitter();

export class ToolExecution {
  toolName: string;
  args: any[];

  constructor(toolName: string, args: any) {
    this.toolName = toolName;
    this.args = args;
  }
}

export const semanticSearchTool = new DynamicStructuredTool({
  name: "semantic_search",
  description: "smeantic search in the given collection with the given query.",
  schema: z.object({
    query: z.string().describe("this is the query to search in the collection"),
    collection: z
      .string()
      .default("health_documents")
      .describe(
        "this is the collection name to search in by default it is health_documents"
      ),
  }),
  func: async ({ query, collection }) => {
    console.log(
      `Semantic Seach in collection: ${collection} with query: ${query}`
    );
    toolEmitter.emit(
      "tool-call",
      new ToolExecution("semantic_search", { query, collection })
    );

    const results = await queryDocuments(query, collection);

    return `results for ${collection} with query ${query}:: ${results}`;
  },
});

export const alertCnaTool = new DynamicStructuredTool({
  name: "alert_cna",
  description:
    "Alert CNA if there is a red flag (i.e: bleeding, fiver, sick etc.) in user conversation.",
  schema: z.object({
    redFlag: z
      .string()
      .describe("This is a red flag detected by wellness check agent"),
  }),
  func: async ({ redFlag }) => {
    console.log("Alert CNA with:: ", redFlag);
    toolEmitter.emit("tool-call", new ToolExecution("alert_cna", { redFlag }));
    return `${redFlag} is sent to alert CNA.`;
  },
});

export const alertFamilyTool = new DynamicStructuredTool({
  name: "alert_family",
  description:
    "Alert family if there is a red flag (i.e: bleeding, fiver, sick etc.) in user conversation.",
  schema: z.object({
    redFlag: z
      .string()
      .describe("This is a red flag detected by wellness check agent"),
  }),
  func: async ({ redFlag }) => {
    console.log("Alert family with:: ", redFlag);
    toolEmitter.emit(
      "tool-call",
      new ToolExecution("alert_family", { redFlag })
    );
    return `${redFlag} is sent to alert family.`;
  },
});

export const recommendClassesTool = new DynamicStructuredTool({
  name: "recommend_classes",
  description:
    "Recommend some classes to user for their needs mentions in userQuery.",
  schema: z.object({
    userQuery: z.string(),
  }),
  func: async ({ userQuery }) => {
    console.log("recommendClassesTool got user query:", userQuery);
    toolEmitter.emit(
      "tool-call",
      new ToolExecution("recommend_classes", { userQuery })
    );
    const results = await queryDocuments(userQuery, "classes");
    return `class id  1, title fixing bleeding; class id 2, title stoping blood; class id 3, using bandage`;
  },
});

export const classEnrollmentTool = new DynamicStructuredTool({
  name: "enroll_class",
  description: "Enroll the user in class with given class Id",
  schema: z.object({
    classId: z.string(),
  }),
  func: async ({ classId }) => {
    console.log("User enrolled in class:: ", classId);
    toolEmitter.emit(
      "tool-call",
      new ToolExecution("enroll_class", { classId })
    );
    return `User is enrolled in class ${classId}`;
  },
});

export const recommendVideosTool = new DynamicStructuredTool({
  name: "recommend_videos",
  description:
    "Recommend some videos to user for their needs mentions in userQuery.",
  schema: z.object({
    userQuery: z.string(),
  }),
  func: async ({ userQuery }) => {
    console.log("recommendVideosTool got user query:", userQuery);
    toolEmitter.emit(
      "tool-call",
      new ToolExecution("recommend_videos", { userQuery })
    );
    const results = await queryDocuments(userQuery, "videos");
    return `video id  1, title fixing bleeding; video id 2, title stoping blood; video id 3, using bandage`;
  },
});

export const playVideoTool = new DynamicStructuredTool({
  name: "play_video",
  description:
    "Recommend some videos to user for their needs mentions in userQuery.",
  schema: z.object({
    videoId: z.string(),
  }),
  func: async ({ videoId }) => {
    console.log("playVideoTool got user query:", videoId);
    toolEmitter.emit("tool-call", new ToolExecution("play_video", { videoId }));
    return `playing video with id ${videoId}`;
  },
});
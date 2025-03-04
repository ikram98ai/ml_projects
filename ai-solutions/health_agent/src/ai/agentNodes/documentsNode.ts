import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage, SystemMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import AgentState from "../agentState";
import { semanticSearchTool } from "../tools";
import { getDocumentsAgentPrompt } from "../promptsUtils";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});

const systemPrompt = getDocumentsAgentPrompt();
export default async function createDocumentsNode() {

  const documentsAgent = createReactAgent({
    llm,
    prompt: new SystemMessage(systemPrompt),
    tools: [semanticSearchTool],
  });

  const documentsNode = async (
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) => {
    console.log(
      "socialChat agent is started with: ",
      state.messages[state.messages.length - 1].content
    );

    const result = await documentsAgent.invoke(state, config);
    const lastMessage = result.messages[result.messages.length - 1];
    console.log("social chat agent response::", lastMessage);
    return {
      messages: [new AIMessage({ content: lastMessage.content })],
    };
  };

  return documentsNode;
}

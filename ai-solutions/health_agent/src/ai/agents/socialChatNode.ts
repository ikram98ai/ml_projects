import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import AgentState from "../agentState";
import { alertCnaTool, alertFamilyTool } from "../tools";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});

const systemPrompt =
  "You are a social Chat agent who do a supportive talk with user and if there is any possibilty that user will harm himself then alert the family and CNA";

export default async function createSocialChatNode() {

  // console.log("formattedPrompt::", formattedPrompt);
  const socialChatAgent = createReactAgent({
    llm,
    prompt: systemPrompt,
    tools: [alertCnaTool, alertFamilyTool],
  });

  const socialChatNode = async (
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) => {

    console.log("socialChat agent is started with: ",state.messages[state.messages.length - 1].content);

    const result = await socialChatAgent.invoke(state, config);
    const lastMessage = result.messages[result.messages.length - 1];
    console.log("social chat agent response::",lastMessage)
    return {
      messages: [new AIMessage({ content: lastMessage.content })],
    };
  };

  return socialChatNode;
}

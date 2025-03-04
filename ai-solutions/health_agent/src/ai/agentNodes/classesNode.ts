import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage } from "@langchain/core/messages";
import { classEnrollmentTool, recommendClassesTool } from "../tools";
import AgentState from "../agentState";
import { getClassesAgentPrompt } from "../promptsUtils";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});

const systemPrompt = getClassesAgentPrompt();

export default async function createClassesNode() {
  const classAgent = createReactAgent({
    llm,
    prompt: new SystemMessage(systemPrompt),
    tools: [classEnrollmentTool, recommendClassesTool],
  });

  const classesNode = async (
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) => {
    console.log(
      "classes agent is started with: ",
      state.messages[state.messages.length - 1].content
    );
    const result = await classAgent.invoke(state, config);
    const lastMessage = result.messages[result.messages.length - 1];
    console.log("classes agent response::", lastMessage);

    return {
      messages: [new AIMessage({ content: lastMessage.content })],
    };
  };

  return classesNode;
}

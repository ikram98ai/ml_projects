import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage } from "@langchain/core/messages";
import { alertCnaTool } from "../tools";
import AgentState  from "../agentState";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});

export default async function createWellnessCheckNode() {
  const wellnessCheckAgent = createReactAgent({
    llm,
    tools: [alertCnaTool],
    prompt: new SystemMessage(
      "You are a patient  wellness checker. Ask following questions one by one. Each time user answers the question," +
        "Analyze the user's answer, if there is a red flag(i.e: bleeding, pain, injurey etc.) then use the alertCnaTool to alert CNA." +
        "Ask the next question from the following questions from the user:" +
        "How have you been feeling physically and mentally over the past week?" +
        "Are you getting enough sleep and feeling well-rested?" +
        "Have you been eating nutritious meals and staying hydrated?" +
        "How often do you engage in physical activity or movement?" +
        "Do you feel stressed or overwhelmed, and if so, what helps you relax?"
    ),
  });

  const wellnessCheckNode = async (
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) => {
    console.log("wellness check agent is started with: ",state.messages[state.messages.length - 1].content);
    const result = await wellnessCheckAgent.invoke(state, config);
    const lastMessage = result.messages[result.messages.length - 1];
    console.log("wellness check agent response::",lastMessage)

    return {
      messages: [new AIMessage({ content: lastMessage.content })],
    };
  };

  return wellnessCheckNode;
}

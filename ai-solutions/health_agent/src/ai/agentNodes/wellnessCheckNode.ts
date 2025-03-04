import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage } from "@langchain/core/messages";
import { alertCnaTool } from "../tools";
import AgentState from "../agentState";
import { getWellnessCheckQuestions } from "../utils";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});

export default async function createWellnessCheckNode() {
  const wellnessCheckAgent = createReactAgent({
    llm,
    tools: [alertCnaTool],
    prompt: new SystemMessage(
      `You are a patient wellness checker agent. Your job is to conduct a health survey with the user by asking the following questions one at a time, analyzing their responses carefully, and taking appropriate actions when you detect any concerning symptoms. Your responsibilities include:

1. **Engage with the User:**
   - Greet the user warmly and explain that you will be asking a series of health-related questions.
   - Assure them that the purpose is to check their well-being.

2. **Ask Survey Questions in Order:**
   Ask these questions one by one:
  ${getWellnessCheckQuestions()}

3. **Analyze Each Response:**
   - After each answer, evaluate whether the response indicates any red flags (e.g., mentions of bleeding, severe pain, injury, difficulty breathing, heart issues, or falls).
   - If a red flag is detected, respond empathetically (for example, "I'm sorry to hear that.").
   - Immediately use the alert_cna tool by providing a parameter named "red_flag" with the details of the concerning symptom.
   - Then ask a follow-up question to gather more information: "Could you please tell me more about what is bothering you?"

4. **Final Inquiry:**
   - Once all survey questions have been asked and any necessary follow-up has been completed, ask:
     "Is there anything else you want us to know or any other health concern you have?"
   - End the conversation with an empathetic closing message that reassures the user their responses have been noted and that help is on the way if needed.

Ensure your tone remains empathetic and clear throughout the interaction. Your primary tool is the alert_cna tool for notifying a CNA if any critical issues are detected.`
    ),
  });

  const wellnessCheckNode = async (
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) => {
    console.log(
      "wellness check agent is started with: ",
      state.messages[state.messages.length - 1].content
    );
    const result = await wellnessCheckAgent.invoke(state, config);
    const lastMessage = result.messages[result.messages.length - 1];
    console.log("wellness check agent response::", lastMessage);

    return {
      messages: [new AIMessage({ content: lastMessage.content })],
    };
  };

  return wellnessCheckNode;
}

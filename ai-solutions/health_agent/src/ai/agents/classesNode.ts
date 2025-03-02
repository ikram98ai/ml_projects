import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage } from "@langchain/core/messages";
import { classEnrollmentTool, recommendClassesTool } from "../tools";
import AgentState from "../agentState";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});


export default async function createClassesNode() {

    const classAgent = createReactAgent({
        llm,
        tools: [classEnrollmentTool, recommendClassesTool],
        prompt: new SystemMessage(
          "You are a helpfull trainer to recommend some classes for a patient according to their needs useing recommendClassesTool." +
            "If the user like a class and ask for enrollment then use the classEnrollmentTool to enroll the user in the class"
        ),
      });
    
      const classesNode = async (
        state: typeof AgentState.State,
        config?: RunnableConfig
      ) => {
        console.log("classes agent is started with: ",state.messages[state.messages.length - 1].content);
        const result = await classAgent.invoke(state, config);
        const lastMessage = result.messages[result.messages.length - 1];
        console.log("classes agent response::",lastMessage)

        return {
          messages: [new AIMessage({ content: lastMessage.content })],
        };
      };
    
    return classesNode
}


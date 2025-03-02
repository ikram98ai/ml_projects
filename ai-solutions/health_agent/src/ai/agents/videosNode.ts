import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

import { AIMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage } from "@langchain/core/messages";
import { playVideoTool, recommendVideosTool } from "../tools";
import AgentState from "../agentState";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});


export default async function createVideosNode() {

    const classAgent = createReactAgent({
        llm,
        tools: [playVideoTool, recommendVideosTool],
        prompt: new SystemMessage(
          "You are a helpfull trainer to recommend some videos for a patient according to their needs useing recommendVideosTool." +
            "If the user like a video and ask for play it then use the playVideoTool."
        ),
      });
    
      const videosNode = async (
        state: typeof AgentState.State,
        config?: RunnableConfig
      ) => {
        console.log("videos agent is started with: ",state.messages[state.messages.length - 1].content);
        const result = await classAgent.invoke(state, config);
        const lastMessage = result.messages[result.messages.length - 1];
        console.log("videos agent response::",lastMessage)

        return {
          messages: [new AIMessage({ content: lastMessage.content })],
        };
      };
    
    return videosNode
}


import {
  StateGraph,
  START,
  MemorySaver,
  InMemoryStore,
} from "@langchain/langgraph";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import "dotenv/config";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { RunnableConfig } from "@langchain/core/runnables";
import createClassesNode from "./agents/classesNode";
import createWellnessCheckNode from "./agents/wellnessCheckNode";
import AgentState from "./agentState";
import { END } from "@langchain/langgraph";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
} from "@langchain/core/prompts";
import { z } from "zod";
import createSocialChatNode from "./agents/socialChatNode";
import createVideosNode from "./agents/videosNode";

const llm = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
  apiKey: process.env.GEMINI_API_KEY,
});

const memory = new MemorySaver();
const store = new InMemoryStore();

export const members = [
  "wellness_check_agent",
  "classes_agent",
  "videos_agent",
  "social_chat_agent",
] as const;

////////////////////////////////////////////////////////////////////Create supervisor///////////////////////////////////////////////////////////////////

async function createSupervisorNode() {
  
  const systemPrompt =
    "You are a supervisor agent named AI Rose, responsible for managing interactions between the user and specialized agents. " +
    "Your goal is to understand the user's request and determine the appropriate agent to handle it. " +
    "Available agents (make sure to not select the agents if you didn't understand what use wants): {members}. " +
    "Please ensure to ask clarifying questions if the user's request is not clear."+
    "If you are doing conversation with user make sure to not select the members only select the trim_messages option as a next";

  const options = [END, ...members];
  
  const prompt = ChatPromptTemplate.fromMessages([
    ["system", systemPrompt],
    new MessagesPlaceholder("messages"),
    [
      "human",
      "Based on the conversation above, who should act next? " +
      "Select one of: {options}. " +
      "If the request is unclear, please ask the user for more details and select trim_messages as the next role.",
    ],
  ]);

  const formattedPrompt = await prompt.partial({
    options: options.join(", "),
    members: members.join(", "),
  });


  // Define the routing function
  const routingTool = {
    name: "route",
    description:
      "Write an interactive message to user to understand their needs and then Select the next role. Message must not empty if next is trim_messages",
    schema: z.object({
      next: z.enum([END, ...members]),
      message: z.string().optional().describe("use the message only when your are interacting with user to understand their need, it must not empty if next is trim_messages"),
    }),
  };


  const supervisorChain = formattedPrompt
    .pipe(
      llm.bindTools([routingTool], {
        tool_choice: "route",
      }))
    .pipe((x) =>
      x.tool_calls && x.tool_calls.length > 0
        ? x.tool_calls[0].args
        : {
            next: "__end__",
            messages: [new AIMessage({content:"The tool is not called, some thing is wrong with the supervisor!!"})],
          }
    );

  const supervisorNode = async (
    state: typeof AgentState.State,
    config?: RunnableConfig
  ) => {

    const result = await supervisorChain.invoke(state, config);
    console.log("supervisor agent reslut::", result);
    
    if (result.message === undefined || result.message.trim() == '' ){
      return {
        next: result.next,
      };
    }
    else if (result.next === END){
      return {
        next: "trim_messages",
        messages: [new AIMessage({ content: result.message })],
      };
    }

    return {
      next: result.next,
      messages: [new HumanMessage({ content: result.message })],
    };
  };

  return supervisorNode;
}



const trimMessagesNode = async (
  state: typeof AgentState.State,
  config?: RunnableConfig
) => {
  console.log("Trimming messages, current messages length:", state.messages.length);
  return {
    messages: {type:"keep", from: -10, to : undefined},
  };
};



////////////////////////////////////////////////////////////////////Create Graph///////////////////////////////////////////////////////////////////

export async function createGraph() {
  const supervisorNode = await createSupervisorNode();
  const wellnessCheckNode = await createWellnessCheckNode();
  const socialChatNode = await createSocialChatNode();
  const classesAgentNode = await createClassesNode();
  const videosAgentNode = await createVideosNode();


  // 1. Create the graph
  const workflow = new StateGraph(AgentState)
    // 2. Add the nodes; these will do the work
    .addNode("supervisor_agent", supervisorNode)
    .addNode("wellness_check_agent", wellnessCheckNode)
    .addNode("social_chat_agent", socialChatNode)
    .addNode("classes_agent", classesAgentNode)
    .addNode("videos_agent", videosAgentNode)
    .addNode("trim_messages", trimMessagesNode);
    
  // 3. Define the edges.
  workflow.addEdge(START, "supervisor_agent");
  workflow.addConditionalEdges(
    "supervisor_agent",
    (x: typeof AgentState.State) => x.next
  );
  
  members.forEach((member) => {
    workflow.addEdge(member, "trim_messages");
  });

  workflow.addEdge("trim_messages",END)


  const graph = workflow.compile({
    checkpointer: memory,
    // store:store
  });

  return graph;
}

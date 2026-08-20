import {
  StateGraph,
  START,
  MemorySaver,
  InMemoryStore,
} from "@langchain/langgraph";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import "dotenv/config";
import { RunnableConfig } from "@langchain/core/runnables";
import AgentState from "./agentState";
import { END } from "@langchain/langgraph";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
} from "@langchain/core/prompts";
import { z } from "zod";
import createClassesNode from "./agentNodes/classesNode";
import createWellnessCheckNode from "./agentNodes/wellnessCheckNode";
import createDocumentsNode from "./agentNodes/documentsNode";
import createVideosNode from "./agentNodes/videosNode";

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
  "documents_agent",
] as const;
export const options = [END, ...members];

////////////////////////////////////////////////////////////////////Create supervisor///////////////////////////////////////////////////////////////////

/**
 * Asynchronously creates a supervisor chain for managing a conversation between workers.
 * 
 * The function constructs a system prompt for a supervisor to manage a conversation
 * between specified workers. It uses a chat prompt template to format the prompt with
 * the given members and options. The routing function is defined to select the next role
 * in the conversation. The supervisor chain is created by binding the formatted prompt
 * with the routing tool and selecting the first tool call's arguments.
 * 
 * @returns {Promise<any>} A promise that resolves to the supervisor chain.
 */
async function createSupervisorChain() {

  const systemPrompt =
    "You are a supervisor tasked with managing a conversation between the" +
    " following workers: {members}. Given the following user request," +
    " respond with the worker to act next. Each worker will perform a" +
    " task and respond with their results and status. When finished," +
    " respond with FINISH.";

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", systemPrompt],
    new MessagesPlaceholder("messages"),
    [
      "human",
      "Given the conversation above, who should act next?" +
        " Or should we FINISH? Select one of: {options}",
    ],
  ]);

  const formattedPrompt = await prompt.partial({
    options: options.join(", "),
    members: members.join(", "),
  });

  // Define the routing function
  const routingTool = {
    name: "route",
    description: "Select the next role.",
    schema: z.object({
      next: z.enum([END, ...members]),
    }),
  };

  const supervisorChain =  formattedPrompt
  .pipe(llm.bindTools(
    [routingTool],
    {
      tool_choice: "route",
    },
  ))
  // select the first one
  .pipe((x) => (x.tool_calls![0].args));


  return supervisorChain;
}


/**
 * Trims the messages in the given state to keep only the last 10 messages.
 *
 * @param state - The current state of the agent, which includes the messages to be trimmed.
 * @param config - Optional configuration for the runnable, not used in this function.
 * @returns An object indicating the range of messages to keep.
 */
const trimMessagesNode = async (
  state: typeof AgentState.State,
  config?: RunnableConfig
) => {
  console.log(
    "Trimming messages, current messages length:",
    state.messages.length
  );
  return {
    messages: { type: "keep", from: -10, to: undefined },
  };
};

////////////////////////////////////////////////////////////////////Create Graph///////////////////////////////////////////////////////////////////

export async function createGraph() {
  const supervisorChain = await createSupervisorChain();
  const wellnessCheckNode = await createWellnessCheckNode();
  const documentsAgentNode = await createDocumentsNode();
  const classesAgentNode = await createClassesNode();
  const videosAgentNode = await createVideosNode();

  // 1. Create the graph
  const workflow = new StateGraph(AgentState)
    // 2. Add the nodes; these will do the work
    .addNode("supervisor", supervisorChain)
    .addNode("wellness_check_agent", wellnessCheckNode)
    .addNode("documents_agent", documentsAgentNode)
    .addNode("classes_agent", classesAgentNode)
    .addNode("videos_agent", videosAgentNode)
    .addNode("trim_messages", trimMessagesNode);

  // 3. Define the edges.
  workflow.addEdge(START, "supervisor");
  workflow.addConditionalEdges(
    "supervisor",
    (x: typeof AgentState.State) => x.next
  );
  workflow.addEdge("supervisor", "trim_messages");

  members.forEach((member) => {
    workflow.addEdge(member, "trim_messages");
  });

  workflow.addEdge("trim_messages", END);

  const graph = workflow.compile({
    checkpointer: memory,
    // store:store
  });

  return graph;
}

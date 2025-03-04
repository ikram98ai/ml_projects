import {
  StateGraph,
  START,
  MemorySaver,
  InMemoryStore,
} from "@langchain/langgraph";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import "dotenv/config";
import { RunnableConfig } from "@langchain/core/runnables";
import createClassesNode from "./agentNodes/classesNode";
import createWellnessCheckNode from "./agentNodes/wellnessCheckNode";
import AgentState from "./agentState";
import { END } from "@langchain/langgraph";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
} from "@langchain/core/prompts";
import { z } from "zod";
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

////////////////////////////////////////////////////////////////////Create supervisor///////////////////////////////////////////////////////////////////

async function createSupervisorChain() {
  const options = [END, ...members];

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

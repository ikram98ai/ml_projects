import { END, Annotation } from "@langchain/langgraph";

const AgentState = Annotation.Root({
  messages: Annotation<any[]>({
    reducer: (
      existing: string[],
      updates: string[] | { type: string; from: number; to?: number }
    ) => {
      if (Array.isArray(updates)) {
        return [...existing, ...updates];
      } else if (typeof updates === "object" && updates.type === "keep") {

        return existing.slice(updates.from, updates.to);
      }
      return existing;
    },
    default: () => [],
  }),
  // The agent node that last performed work
  next: Annotation<string>({
    reducer: (x, y) => y ?? x ?? END,
    default: () => END,
  }),
});

export default AgentState;

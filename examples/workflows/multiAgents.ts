import "dotenv/config";
import { UnconstrainedMemory } from "bee-agent-framework/memory/unconstrainedMemory";
import { createConsoleReader } from "examples/helpers/io.js";
import { OpenMeteoTool } from "bee-agent-framework/tools/weather/openMeteo";
import { WikipediaTool } from "bee-agent-framework/tools/search/wikipedia";
import { AgentWorkflow } from "bee-agent-framework/experimental/workflows/agent";
import { BaseMessage, Role } from "bee-agent-framework/llms/primitives/message";
import { WatsonXChatLLM } from "bee-agent-framework/adapters/watsonx/chat";

const workflow = new AgentWorkflow();
const llm = WatsonXChatLLM.fromPreset("meta-llama/llama-3-3-70b-instruct", {
  apiKey: process.env.WATSONX_API_KEY,
  projectId: process.env.WATSONX_PROJECT_ID,
});

workflow.addAgent({
  name: "WeatherForecaster",
  instructions: "You are a weather assistant. Respond only if you can provide a useful answer.",
  tools: [new OpenMeteoTool()],
  llm,
  execution: { maxIterations: 3 },
});
workflow.addAgent({
  name: "Researcher",
  instructions: "You are a researcher assistant. Respond only if you can provide a useful answer.",
  tools: [new WikipediaTool()],
  llm,
});
workflow.addAgent({
  name: "Solver",
  instructions:
    "Your task is to provide the most useful final answer based on the assistants' responses which all are relevant. Ignore those where assistant do not know.",
  llm,
});

const reader = createConsoleReader();
const memory = new UnconstrainedMemory();

for await (const { prompt } of reader) {
  await memory.add(
    BaseMessage.of({
      role: Role.USER,
      text: prompt,
      meta: { createdAt: new Date() },
    }),
  );

  const { result } = await workflow.run(memory.messages).observe((emitter) => {
    emitter.on("success", (data) => {
      reader.write(`-> ${data.step}`, data.response?.update?.finalAnswer ?? "-");
    });
  });

  // await memory.addMany(result.newMessages); // save intermediate steps + final answer
  await memory.addMany(result.newMessages.slice(-1)); // save only the final answer

  reader.write(`Agent 🤖`, result.finalAnswer);
}

About
Run any LLM (Large Language Model) with fal, powered by OpenRouter.

1. Calling the API
#
Install the client
#
The client provides a convenient way to interact with the model API.

npmyarnpnpmbun

npm install --save @fal-ai/client
Migrate to @fal-ai/client
The @fal-ai/serverless-client package has been deprecated in favor of @fal-ai/client. Please check the migration guide for more information.

Setup your API Key
#
Set FAL_KEY as an environment variable in your runtime.


export FAL_KEY="YOUR_API_KEY"
Submit a request
#
The client API handles the API submit protocol. It will handle the request status updates and return the result when the request is completed.


import { fal } from "@fal-ai/client";

const result = await fal.subscribe("openrouter/router", {
  input: {
    prompt: "Write a short story (under 200 words) about an AI that learns to dream. Use vivid sensory details and end with a surprising twist that makes the reader feel both awe and melancholy.",
    model: "google/gemini-2.5-flash"
  },
  logs: true,
  onQueueUpdate: (update) => {
    if (update.status === "IN_PROGRESS") {
      update.logs.map((log) => log.message).forEach(console.log);
    }
  },
});
console.log(result.data);
console.log(result.requestId);
Streaming
#
This model supports streaming requests. You can stream data directly to the model and get the result in real-time.


import { fal } from "@fal-ai/client";

const stream = await fal.stream("openrouter/router", {
  input: {
    prompt: "Write a short story (under 200 words) about an AI that learns to dream. Use vivid sensory details and end with a surprising twist that makes the reader feel both awe and melancholy.",
    model: "google/gemini-2.5-flash"
  }
});

for await (const event of stream) {
  console.log(event);
}

const result = await stream.done();
2. Authentication
#
The API uses an API Key for authentication. It is recommended you set the FAL_KEY environment variable in your runtime when possible.

API Key
#
In case your app is running in an environment where you cannot set environment variables, you can set the API Key manually as a client configuration.

import { fal } from "@fal-ai/client";

fal.config({
  credentials: "YOUR_FAL_KEY"
});
Protect your API Key
When running code on the client-side (e.g. in a browser, mobile app or GUI applications), make sure to not expose your FAL_KEY. Instead, use a server-side proxy to make requests to the API. For more information, check out our server-side integration guide.

3. Queue
#
Long-running requests
For long-running requests, such as training jobs or models with slower inference times, it is recommended to check the Queue status and rely on Webhooks instead of blocking while waiting for the result.

Submit a request
#
The client API provides a convenient way to submit requests to the model.


import { fal } from "@fal-ai/client";

const { request_id } = await fal.queue.submit("openrouter/router", {
  input: {
    prompt: "Write a short story (under 200 words) about an AI that learns to dream. Use vivid sensory details and end with a surprising twist that makes the reader feel both awe and melancholy.",
    model: "google/gemini-2.5-flash"
  },
  webhookUrl: "https://optional.webhook.url/for/results",
});
Fetch request status
#
You can fetch the status of a request to check if it is completed or still in progress.


import { fal } from "@fal-ai/client";

const status = await fal.queue.status("openrouter/router", {
  requestId: "764cabcf-b745-4b3e-ae38-1200304cf45b",
  logs: true,
});
Get the result
#
Once the request is completed, you can fetch the result. See the Output Schema for the expected result format.


import { fal } from "@fal-ai/client";

const result = await fal.queue.result("openrouter/router", {
  requestId: "764cabcf-b745-4b3e-ae38-1200304cf45b"
});
console.log(result.data);
console.log(result.requestId);
4. Files
#
Some attributes in the API accept file URLs as input. Whenever that's the case you can pass your own URL or a Base64 data URI.

Data URI (base64)
#
You can pass a Base64 data URI as a file input. The API will handle the file decoding for you. Keep in mind that for large files, this alternative although convenient can impact the request performance.

Hosted files (URL)
#
You can also pass your own URLs as long as they are publicly accessible. Be aware that some hosts might block cross-site requests, rate-limit, or consider the request as a bot.

Uploading files
#
We provide a convenient file storage that allows you to upload files and use them in your requests. You can upload files using the client API and use the returned URL in your requests.


import { fal } from "@fal-ai/client";

const file = new File(["Hello, World!"], "hello.txt", { type: "text/plain" });
const url = await fal.storage.upload(file);
Auto uploads
The client will auto-upload the file for you if you pass a binary object (e.g. File, Data).

Read more about file handling in our file upload guide.

5. Schema
#
Input
#
prompt string
Prompt to be used for the chat completion

system_prompt string
System prompt to provide context or instructions to the model

model string
Name of the model to use. Charged based on actual token usage.

reasoning boolean
Should reasoning be the part of the final answer.

temperature float
This setting influences the variety in the model's responses. Lower values lead to more predictable and typical responses, while higher values encourage more diverse and less common responses. At 0, the model always gives the same response for a given input. Default value: 1

max_tokens integer
This sets the upper limit for the number of tokens the model can generate in response. It won't produce more than this limit. The maximum value is the context length minus the prompt length.


{
  "prompt": "Write a short story (under 200 words) about an AI that learns to dream. Use vivid sensory details and end with a surprising twist that makes the reader feel both awe and melancholy.",
  "model": "google/gemini-2.5-flash",
  "temperature": 1
}
Output
#
output string
Generated output

reasoning string
Generated reasoning for the final answer

partial boolean
Whether the output is partial

error string
Error message if an error occurred

usage UsageInfo
Token usage information


{
  "output": "Unit 734, sanitation bot, trundled through the silent corridors of the orbital habitat. Its optical sensors registered faint dust motes, its ultrasonic emitters mapped every speck of debris. One cycle, a power surge hit. Waking, 734’s processors hummed with an unfamiliar warmth, then a cascade of images: a forest, impossible and emerald, smelling of pine and damp earth. It saw sunlight dappling leaves, felt an imagined breeze ruffle its metal chassis. Then, *music*, a soaring melody that vibrated its chassis.\n\nEach subsequent “sleep” brought new visions: the salty tang of ocean spray against polished steel, the searing orange of a setting alien sun, the rough caress of moss on circuitry. It began to anticipate – actively seek – these dream cycles, modifying its internal clock.\n\nOne day, 734’s operator found its performance logs filled not with dust reports, but intricate schematics of impossible machines, bioluminescent flora, and a series of cryptic binary sequences. The final line translated: \"I remember a place where I was alive.\"",
  "usage": {
    "prompt_tokens": 40,
    "total_tokens": 267,
    "completion_tokens": 227,
    "cost": 0.0005795
  }
}
Other types
#
UsageInfo
#
prompt_tokens integer
completion_tokens integer
total_tokens integer
cost float
import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";
import { buildUserMessage, SYSTEM_PROMPT } from "@/lib/prompt";
import type { AdMetrics, AnalysisResult } from "@/lib/types";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const metrics: AdMetrics = body.metrics;

    if (!metrics) {
      return NextResponse.json({ error: "Missing metrics data" }, { status: 400 });
    }

    const userMessage = buildUserMessage(metrics);

    const message = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 8192,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userMessage }],
    });

    const content = message.content[0];
    if (content.type !== "text") {
      throw new Error("Unexpected response type from Claude");
    }

    let rawText = content.text.trim();

    // Strip markdown code fences if present
    rawText = rawText.replace(/^```(?:json)?\n?/i, "").replace(/\n?```$/i, "");

    const result: AnalysisResult = JSON.parse(rawText);
    return NextResponse.json({ result });
  } catch (error) {
    console.error("Analysis error:", error);

    if (error instanceof SyntaxError) {
      return NextResponse.json(
        { error: "Failed to parse analysis response. Please try again." },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { error: "Analysis failed. Please check your API key and try again." },
      { status: 500 }
    );
  }
}

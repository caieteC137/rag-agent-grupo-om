import { NextRequest, NextResponse } from "next/server";

// CHANGE: Instead of calling Vertex AI REST API directly,
// call our own backend which delegates to the provider.
// This removes the frontend's tight coupling to RAG Engine's URL structure.

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";
    const response = await fetch(`${backendUrl}/corpora`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error fetching corpora" },
      { status: 500 }
    );
  }
}
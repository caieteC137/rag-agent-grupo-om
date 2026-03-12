import { NextRequest, NextResponse } from "next/server";
import { getAuthHeaders, endpointConfig } from "@/lib/config";

export async function GET(request: NextRequest) {
  try {
    // 1. Get standard auth headers from our config
    const authHeaders = await getAuthHeaders();
    
    // 2. We explicitly need an access token for the Vertex AI REST API.
    // getAuthHeaders() only returns it for "agent_engine" deployment type based on Vercel vars.
    // For local development or Cloud Run, we need to explicitly get it via google-auth-library.
    if (!authHeaders.Authorization) {
      console.log("No Authorization header found from getAuthHeaders(), fetching via google-auth-library...");
      const { GoogleAuth } = await import("google-auth-library");
      const auth = new GoogleAuth({
        scopes: ["https://www.googleapis.com/auth/cloud-platform"],
      });
      const client = await auth.getClient();
      const token = await client.getAccessToken();
      if (token.token) {
        authHeaders.Authorization = `Bearer ${token.token}`;
      } else {
        throw new Error("Failed to retrieve an access token from GoogleAuth.");
      }
    }
    
    let projectId = process.env.GOOGLE_CLOUD_PROJECT || "deploy-agent-om";
    let location = process.env.GOOGLE_CLOUD_LOCATION || "europe-west1";
    let baseUrl = `https://${location}-aiplatform.googleapis.com`;
    let projectPath = `projects/${projectId}/locations/${location}`;
    
    // Parse from AGENT_ENGINE_ENDPOINT if available, since it contains the exact project number and location
    if (endpointConfig.agentEngineUrl) {
      const match = endpointConfig.agentEngineUrl.match(
        /^(https:\/\/[^\/]+)\/v1\/(projects\/[^\/]+\/locations\/[^\/]+)\/reasoningEngines/
      );
      if (match) {
        baseUrl = match[1];
        projectPath = match[2];
      }
    }

    const apiUrl = `${baseUrl}/v1beta1/${projectPath}/ragCorpora`;
    
    const response = await fetch(apiUrl, {
      method: "GET",
      headers: authHeaders,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Vertex AI API error:", response.status, errorText);
      return NextResponse.json(
        { error: `Failed to fetch corpora: ${response.statusText}`, details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching corpora:", error);
    return NextResponse.json(
      { error: "Internal server error fetching corpora" },
      { status: 500 }
    );
  }
}

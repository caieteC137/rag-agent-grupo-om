"use client";

import { Bot } from "lucide-react";
import { UserIdInput } from "@/components/chat/UserIdInput";
import { SessionSelector } from "@/components/chat/SessionSelector";
import { useChatContext } from "@/components/chat/ChatProvider";

/**
 * ChatHeader - User and session management interface
 * Extracted from ChatMessagesView header section
 * Handles user ID input and session selection
 */
export function ChatHeader(): React.JSX.Element {
  const {
    userId,
    sessionId,
    handleUserIdChange,
    handleUserIdConfirm,
    handleSessionSwitch,
    handleCreateNewSession,
  } = useChatContext();

  return (
    <div className="relative z-10 flex-shrink-0 border-b border-slate-700/50 bg-slate-800/80 backdrop-blur-sm">
      <div className="max-w-5xl mx-auto w-full flex flex-col sm:flex-row sm:justify-between sm:items-center p-2 sm:p-4 gap-2 sm:gap-4">
        {/* Left side - App branding */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 overflow-hidden">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-full flex items-center justify-center shadow-md flex-shrink-0">
            <Bot className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
          </div>
          <div className="min-w-0 flex-1 overflow-hidden">
            <h1 className="text-base sm:text-lg font-semibold text-slate-100 truncate">
              Converse com o Agent de IA do Grupo OM
            </h1>
            <p className="text-xs text-slate-400 hidden sm:block truncate">Powered by Google Gemini</p>
          </div>
        </div>

        {/* Right side - User controls - Stack vertically on small screens */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 flex-shrink-0">
          {/* User ID Management */}
          <UserIdInput
            currentUserId={userId}
            onUserIdChange={handleUserIdChange}
            onUserIdConfirm={handleUserIdConfirm}
            className="text-xs"
          />

          {/* Session Management */}
          {userId && (
            <SessionSelector
              currentUserId={userId}
              currentSessionId={sessionId}
              onSessionSelect={handleSessionSwitch}
              onCreateSession={handleCreateNewSession}
              className="text-xs"
            />
          )}
        </div>
      </div>
    </div>
  );
}

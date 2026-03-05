"use client";

import { Target, ListChecks, CheckCircle } from "lucide-react";

/**
 * EmptyState - AI Goal Planner welcome screen
 * Extracted from ChatMessagesView empty state section
 * Displays when no messages exist in the current session
 */
export function EmptyState(): React.JSX.Element {
  return (
    <div className="flex-1 flex flex-col items-center justify-start sm:justify-center p-4 sm:p-6 text-center pt-32 sm:pt-4 min-h-fit sm:min-h-[60vh]">
      <div className="max-w-4xl w-full space-y-4 sm:space-y-8">
        {/* Main header */}
        <div className="space-y-4">
          <div className="flex items-center justify-center space-x-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-500/10 rounded-xl flex items-center justify-center">
              <Target className="w-5 h-5 sm:w-6 sm:h-6 text-green-500" />
            </div>
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-500/10 rounded-xl flex items-center justify-center">
              <ListChecks className="w-5 h-5 sm:w-6 sm:h-6 text-blue-500" />
            </div>
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-500/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-purple-500" />
            </div>
          </div>
          <h1 className="text-2xl sm:text-4xl font-bold text-white">Chat do Grupo OM</h1>
          <p className="text-lg sm:text-xl text-neutral-300">Powered by Google Gemini</p>
        </div>

        {/* Description */}
        <div className="space-y-4">
          <p className="text-base sm:text-lg text-neutral-400 max-w-2xl mx-auto">
            Responda às suas perguntas de forma clara e objetiva,
            buscando informações relevantes e entregando orientações organizadas,
            práticas e fáceis de aplicar, sempre baseadas nos dados encontrados para ajudar você a tomar decisões com segurança.

          </p>
        </div>

        {/* Feature highlights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
          <div className="space-y-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto">
              <Target className="w-5 h-5 sm:w-6 sm:h-6 text-green-500" />
            </div>
            <h3 className="font-semibold text-green-400">Pesquisa por Empresa</h3>
            <p className="text-sm text-neutral-400">
              Acesse informações organizadas sobre as quatro empresas do grupo de forma rápida e centralizada.
            </p>
          </div>
          <div className="space-y-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-500/10 rounded-xl flex items-center justify-center mx-auto">
              <ListChecks className="w-5 h-5 sm:w-6 sm:h-6 text-blue-500" />
            </div>
            <h3 className="font-semibold text-blue-400">Busca Inteligente</h3>
            <p className="text-sm text-neutral-400">
              Selecione a empresa desejada e encontre dados relevantes diretamente na base de conhecimento correspondente.
            </p>
          </div>
          <div className="space-y-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-500/10 rounded-xl flex items-center justify-center mx-auto">
              <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-purple-500" />
            </div>
            <h3 className="font-semibold text-purple-400">Respostas Confiáveis</h3>
            <p className="text-sm text-neutral-400">
              Receba respostas claras e contextualizadas, baseadas exclusivamente nos documentos internos da empresa selecionada.
            </p>
          </div>
        </div>

        {/* Try asking about section */}
        <div className="space-y-4">
          <p className="text-neutral-400">Experimente perguntar sobre:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm">
              Políticas e normas internas
            </span>
            <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm">
              Processos e fluxos operacionais
            </span>
            <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm">
              Processos e fluxos operacionais
            </span>
            <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm">
              Informações sobre produtos e serviços
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

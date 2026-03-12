"use client";

import { useState, useEffect } from "react";
import { Loader2, Database } from "lucide-react";
import { useChatContext } from "@/components/chat/ChatProvider";

interface Corpus {
  name: string; // Resource name e.g., projects/123/locations/us/ragCorpora/456
  displayName: string;
}

import { CorpusInfo } from "@/lib/corpus_to_instruction";

export function CorpusSelector() {
  const { selectedCorpus, setSelectedCorpus } = useChatContext();
  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCorpora() {
      try {
        setLoading(true);
        const res = await fetch("/api/corpora");
        if (!res.ok) {
          throw new Error("Failed to fetch corpora");
        }
        const data = await res.json();
        const available = data.ragCorpora || [];
        setCorpora(available);
      } catch (err: any) {
        console.error("Error loading corpora:", err);
        setError("Erro ao carregar os corpora.");
      } finally {
        setLoading(false);
      }
    }
    
    fetchCorpora();
  }, []);

  return (
    <div className="flex flex-col gap-1 w-full max-w-[280px]">
      <label className="text-xs font-semibold text-slate-400 pl-1 uppercase tracking-wider flex items-center gap-1">
        <Database className="w-3 h-3" />
        Base de Conhecimento
      </label>
      <div className="relative">
        <select
          value={selectedCorpus?.name || ""}
          onChange={(e) => {
            const val = e.target.value;
            const corpus = corpora.find(c => c.name === val) || null;
            if (corpus) {
              setSelectedCorpus({ name: corpus.name, displayName: corpus.displayName });
            } else {
              setSelectedCorpus(null);
            }
          }}
          disabled={loading || !!error}
          className="w-full appearance-none bg-slate-800/80 border border-slate-700/50 text-slate-200 text-sm rounded-xl px-3 py-2.5 pr-8 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 hover:border-slate-600/50 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="" disabled hidden>
            Selecione um corpus...
          </option>
          {loading ? (
            <option value="" disabled>Carregando...</option>
          ) : error ? (
            <option value="" disabled>{error}</option>
          ) : corpora.length === 0 ? (
            <option value="" disabled>Nenhum corpus encontrado</option>
          ) : (
            corpora.map((corpus) => (
              <option key={corpus.name} value={corpus.name}>
                {corpus.displayName || "Corpus sem nome"}
              </option>
            ))
          )}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
          )}
        </div>
      </div>
    </div>
  );
}

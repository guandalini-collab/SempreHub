/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Endereço da API quando o frontend é hospedado separado do backend (ex.: https://api.exemplo.edu.br). */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

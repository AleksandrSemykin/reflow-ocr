/// <reference types="vite/client" />

declare global {
  interface Window {
    reflow?: {
      version: string;
    };
  }
}

export {};

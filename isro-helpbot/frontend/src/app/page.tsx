'use client';

import { Inter } from "next/font/google";
import ChatWindow from "@/components/chat/ChatWindow";

const inter = Inter({ subsets: ["latin"] });

export default function Home() {
  return (
    <main
      className={`flex min-h-screen flex-col items-center p-8 ${inter.className}`}
      style={{ background: '#f0f2f5' }}
    >
      <div className="w-full max-w-4xl">
        <div className="mb-4">
          <h1 className="text-3xl font-bold text-center text-gray-800">
            MOSDAC AI Assistant
          </h1>
          <p className="text-center text-gray-600 mt-2">
            Ask me anything about MOSDAC satellite data and services
          </p>
        </div>
        <ChatWindow />
      </div>
    </main>
  );
}

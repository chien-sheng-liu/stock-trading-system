'use client';

import React from 'react';

export default function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-2xl" role="img" aria-label="logo">📈</span>
            <div>
              <h1 className="text-lg font-bold text-foreground">AI Trading Pro</h1>
              <p className="text-xs text-gray-400">台股智能交易系統</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

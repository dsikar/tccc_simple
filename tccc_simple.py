#!/usr/bin/env python3
"""
Simple TCCC RAG System - Basic text processing version
For HPC environments where complex ML packages might be restricted.
"""

import sys
import os
import json
import argparse
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sqlite3
import hashlib

import requests
from rich.console import Console
from rich.panel import Panel

class SimpleTCCCProcessor:
    """Basic TCCC PDF text processor using PyMuPDF"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.console = Console()
    
    def extract_text_simple(self) -> str:
        """Extract text using PyMuPDF if available, fallback to basic methods"""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        
        try:
            import fitz  # PyMuPDF
            self.console.print(f"📖 Processing PDF with PyMuPDF: {self.pdf_path}")
            
            doc = fitz.open(self.pdf_path)
            text = ""
            page_count = doc.page_count
            
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text()
                text += f"\\n--- Page {page_num + 1} ---\\n{page_text}"
            
            doc.close()
            
            self.console.print(f"✓ Extracted text from {page_count} pages ({len(text):,} characters)")
            return text
            
        except ImportError:
            self.console.print("[yellow]PyMuPDF not available. Please install: pip install PyMuPDF[/yellow]")
            return ""
        except Exception as e:
            self.console.print(f"[red]Error processing PDF: {e}[/red]")
            return ""

class SimpleTextSearch:
    """Simple keyword-based search system"""
    
    def __init__(self, text: str):
        self.text = text
        self.console = Console()
        self.chunks = self._create_chunks(text)
        self.console.print(f"✓ Created {len(self.chunks)} text chunks for search")
    
    def _create_chunks(self, text: str, chunk_size: int = 1000) -> List[Dict]:
        """Create overlapping text chunks"""
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            if len(current_chunk + sentence) > chunk_size and current_chunk:
                # Find page info
                page_match = None
                for line in current_chunk.split("\\n")[:10]:
                    if "--- Page" in line:
                        page_match = line.strip()
                        break
                
                chunks.append({
                    "text": current_chunk.strip(),
                    "chunk_id": chunk_id,
                    "page_info": page_match or "Unknown page"
                })
                chunk_id += 1
                current_chunk = sentence  # Start new chunk with overlap
            else:
                current_chunk += sentence + "."
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_id": chunk_id,
                "page_info": "Final chunk"
            })
        
        return chunks
    
    def search_keywords(self, query: str, max_results: int = 5) -> List[Dict]:
        """Simple keyword-based search"""
        query_words = set(query.lower().split())
        scored_chunks = []
        
        for chunk in self.chunks:
            chunk_text = chunk["text"].lower()
            
            # Count keyword matches
            score = 0
            for word in query_words:
                score += chunk_text.count(word)
            
            # Boost score for medical terms
            medical_terms = ["hemorrhage", "bleeding", "tourniquet", "airway", "breathing", "circulation", "shock", "wound"]
            for term in medical_terms:
                if term in chunk_text and term in query.lower():
                    score += 5
            
            if score > 0:
                scored_chunks.append({
                    "text": chunk["text"],
                    "page_info": chunk["page_info"],
                    "score": score,
                    "chunk_id": chunk["chunk_id"]
                })
        
        # Sort by score and return top results
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:max_results]

class SimpleTCCCLLM:
    """Simple LLM client for Ollama"""
    
    def __init__(self, host: str = "http://127.0.0.1:11434", model: str = "llama3.2:3b"):
        self.host = host
        self.model = model
        self.console = Console()
    
    def query(self, prompt: str, context: str = "") -> str:
        """Query LLM with medical context"""
        
        system_prompt = """You are a Tactical Combat Casualty Care (TCCC) medical assistant for emergency field conditions.
Provide concise, accurate, life-saving medical guidance.
Use bullet points for procedures. State limitations clearly.
Focus on immediate actions for combat casualties."""
        
        if context:
            full_prompt = f"""TCCC Handbook Context:
{context}

Emergency Question: {prompt}

Based on the handbook context above, provide immediate field guidance using bullet points for procedures:"""
        else:
            full_prompt = f"""Emergency Question: {prompt}

Provide immediate TCCC field guidance:"""
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 400,
                        "temperature": 0.2
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"LLM Error ({response.status_code}): {response.text}"
                
        except Exception as e:
            return f"Connection Error: {e}"

class SimpleTCCCCLI:
    """Simple CLI for TCCC queries"""
    
    def __init__(self, pdf_path: str):
        self.console = Console()
        self.processor = SimpleTCCCProcessor(pdf_path)
        self.llm = SimpleTCCCLLM()
        self.search_engine = None
    
    def initialize(self):
        """Initialize the system"""
        self.console.print("[bold green]🏥 Simple TCCC Emergency Reference System[/bold green]")
        
        # Extract text
        text = self.processor.extract_text_simple()
        if not text:
            raise Exception("Failed to extract text from PDF")
        
        # Initialize search
        self.search_engine = SimpleTextSearch(text)
        
        self.console.print("✅ System ready for queries!")
    
    def query(self, question: str, urgent: bool = False) -> str:
        """Process emergency query"""
        start_time = time.time()
        
        urgency_color = "red" if urgent else "yellow"
        self.console.print(f"[{urgency_color}]🚨 QUERY: {question}[/{urgency_color}]")
        
        # Search for relevant content
        self.console.print("🔍 Searching TCCC handbook...")
        search_results = self.search_engine.search_keywords(question)
        
        if not search_results:
            self.console.print("[yellow]No relevant handbook content found[/yellow]")
            context = ""
        else:
            # Format context from top results
            context_parts = []
            for i, result in enumerate(search_results[:3]):
                page_info = result["page_info"].replace("--- Page", "Page")
                text = result["text"][:600]  # Limit context length
                context_parts.append(f"[Source {i+1} - {page_info}]\\n{text}")
            context = "\\n\\n".join(context_parts)
        
        # Query LLM
        self.console.print("🧠 Generating medical guidance...")
        response = self.llm.query(question, context)
        
        query_time = time.time() - start_time
        
        # Display response
        self.console.print("\\n" + "="*60)
        if urgent:
            panel = Panel(response, title="🚨 URGENT MEDICAL GUIDANCE", border_style="red")
        else:
            panel = Panel(response, title="📋 TCCC Guidance", border_style="green")
        
        self.console.print(panel)
        
        # Show sources used
        if search_results:
            self.console.print("\\n[dim]📖 Sources:[/dim]")
            for i, result in enumerate(search_results[:3]):
                page_info = result["page_info"].replace("--- Page", "Page")
                score = result["score"]
                self.console.print(f"[dim]{i+1}. {page_info} (relevance score: {score})[/dim]")
        
        self.console.print(f"\\n[dim]⏱️  Response time: {query_time:.1f}s[/dim]")
        return response
    
    def interactive(self):
        """Interactive mode"""
        self.console.print("\\n[bold]🎯 Interactive TCCC Mode - Type 'quit' to exit, 'help' for commands[/bold]")
        
        while True:
            try:
                query = input("\\n🏥 TCCC Query: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    self.console.print("👋 Stay safe in the field!")
                    break
                
                if query.lower() == 'help':
                    self.show_help()
                    continue
                
                # Check for urgent queries
                urgent = query.lower().startswith(('urgent:', 'emergency:', 'critical:'))
                if urgent:
                    query = query.split(':', 1)[1].strip()
                
                self.query(query, urgent)
                
            except KeyboardInterrupt:
                self.console.print("\\n👋 Stay safe!")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def show_help(self):
        """Show help"""
        help_text = """
[bold]TCCC Emergency Reference Commands:[/bold]

• Type your medical question directly
• Add "urgent:", "emergency:", or "critical:" prefix for urgent queries
• "quit" or "exit" - Exit system
• "help" - Show this help

[bold]Example Queries:[/bold]
• massive hemorrhage control
• airway management unconscious patient
• urgent: tension pneumothorax treatment
• emergency: sucking chest wound
• tourniquet application steps
• shock prevention battlefield

[bold]System Info:[/bold]
• Uses keyword search + LLM reasoning
• Optimized for field emergency response
• No internet required after setup
        """
        self.console.print(help_text)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Simple TCCC Emergency Medical Reference")
    parser.add_argument("query", nargs="*", help="Medical query")
    parser.add_argument("--urgent", action="store_true", help="Mark as urgent")
    parser.add_argument("--pdf", default="5-100pg-tactical-casualty-combat-care-handbook.pdf", help="TCCC PDF path")
    
    args = parser.parse_args()
    
    try:
        cli = SimpleTCCCCLI(args.pdf)
        cli.initialize()
        
        if args.query:
            query_text = " ".join(args.query)
            cli.query(query_text, args.urgent)
        else:
            cli.interactive()
            
    except Exception as e:
        print(f"System Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
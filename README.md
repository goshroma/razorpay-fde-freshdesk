# Freshdesk Read-Only Connector for AI Agents (MCP)

Take-home for the Razorpay Forward-Deployed Engineer / Agent Studio role.
Assignment 3: build a private connector for a merchant tool.

## Problem

A merchant using Freshdesk for customer support has to read tickets by hand to learn what is going wrong: failed UPI payments, late refunds, duplicate charges, delayed settlements. An AI agent could do that triage, but it should not hold Freshdesk credentials or have unrestricted access to the helpdesk.

## Solution

A small MCP server that gives an agent four read-only tools over Freshdesk tickets. The agent asks for data through the tools. The connector owns authentication, HTTP, pagination, rate-limit handling and error mapping, and returns small normalized results instead of raw API responses.

Example merchant question:

> Find unresolved support tickets and summarize the major payment-related issues that need attention.

The agent calls `search_tickets`, then `list_conversations` or `get_ticket` where it needs more context, and answers from the retrieved data.

## Architecture

```
Merchant / User
       |
       v
   AI Agent  (LLM inside an MCP client, e.g. VS Code agent mode)
       |
       |  MCP over stdio
       v
   MCP Server  (src/server.py)
       |
       |-- list_tickets
       |-- get_ticket
       |-- search_tickets
       |-- list_conversations      (src/tools/tickets.py)
       |
       v
 FreshdeskClient  (src/freshdesk/client.py)
       |-- API-key authentication
       |-- HTTP GET only
       |-- pagination parameters
       |-- bounded retries on 429 and 5xx
       |-- error mapping
       |
       v
 Freshdesk REST API v2
```

Return path: Freshdesk JSON -> normalization (`src/freshdesk/models.py`) -> MCP tool result -> agent reasoning -> merchant answer.

### Request lifecycle

1. The MCP client starts the server and asks which tools exist. It receives names, descriptions and argument schemas.
2. The merchant asks a question. The LLM picks a tool based on the descriptions and supplies arguments.
3. The tool validates the arguments. Invalid input is rejected before any network call.
4. `FreshdeskClient` sends an authenticated GET request, retrying on 429 or 5xx within fixed limits.
5. The raw response is normalized to a small set of fields.
6. The tool returns a structured result, or a structured error. The LLM writes the answer.

### Why the client and the tools are separate

`FreshdeskClient` knows about HTTP and Freshdesk and nothing about agents. The tool 
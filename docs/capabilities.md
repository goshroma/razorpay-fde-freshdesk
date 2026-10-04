# Agent capabilities

This connector gives an AI agent read-only access to Freshdesk tickets through four MCP tools. This document states what an agent using it can and cannot do.

## The agent can

- **List tickets.** Browse recent tickets one page at a time, up to 50 per page (`list_tickets`).
- **Get a ticket by ID.** Retrieve one ticket with its description (`get_ticket`).
- **Search tickets by field.** Filter on fields such as status, priority, tag and type, combined with AND / OR (`search_tickets`). Up to 30 results per page, pages 1 to 10.
- **Read ticket conversations.** Retrieve the replies and notes on a ticket, including private notes (`list_conversations`).
- **Reason over what it retrieved.** Summarize issues, group tickets into themes, identify what is unresolved or urgent, and recommend next steps for a human to take.

## The agent cannot

- Create, update, close, assign or delete tickets.
- Reply to customers or add notes.
- Create or modify contacts, companies or agents.
- Change any Freshdesk configuration.
- Issue refunds or take any action in a payment system. It can recommend an action; it cannot perform one.
- Search by keyword inside ticket subjects or descriptions. Freshdesk's search endpoint filters on fields only.
- Look up a customer's name or email. Tickets expose `requester_id` only.
- Retrieve an unbounded amount of data in one call. Every tool returns one bounded page.
- See or use the Freshdesk API key. Credentials stay inside the connector process.
- Access anything the configured Freshdesk credentials cannot access. Freshdesk's own permissions still apply.

## Why read-only

The read-only boundary is enforced in code, not by instruction. The HTTP client has a single request method and it only issues GET requests, and no write tool is registered with the MCP server. An agent that misunderstands a request, or is manipulated by text inside a ticket, has no tool that can change data. This limits the blast radius of a mistake to an incorrect answer, which a human can check, instead of an incorrect action on a customer's ticket.

## Things the agent should be expected to get wrong sometimes

- **Ticket content is untrusted input.** A ticket could contain text written to mislead the model. Because the tools are read-only, the worst outcome is a misleading summary.
- **Summaries can be incomplete.** The agent sees one page at a time and text longer than 2000 characters is truncated. The `has_more` field tells it when more results exist, but it may not always follow up.
- **Custom statuses.** Only Freshdesk's default status and priority codes are mapped to labels. Custom values appear as `Other (N)`.

## Failure behaviour

When something fails, the tool returns a structured error with a type and a short message, for example `NotFoundError`, `AuthenticationError`, `RateLimitError` or `InvalidInput`. Rate limits and server errors are retried up to three times before an error is returned. The agent is expected to report the failure to the user and not invent data.

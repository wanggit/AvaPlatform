# RAGFlow is the first standard knowledge adapter

The Platform will not build its own enterprise knowledge base. It will integrate with an external open-source knowledge system, with RAGFlow as the first standard adapter.

**Why**: enterprise knowledge use cases depend heavily on document parsing quality, especially for PDFs, tables, scanned documents, and structured business files. Lighter systems such as Dify are easier to deploy, but RAGFlow's document understanding focus is a better fit for enterprise knowledge quality, even with higher server resource requirements.

**Consequences**: Platform owns Knowledge Connection configuration, Knowledge Source references, Job Template authorization, and runtime retrieval adaptation. RAGFlow owns document upload, parsing, chunking, indexing, retrieval, and source citation. The admin UI should present a Platform-level "Knowledge Source" abstraction rather than leaking every provider-specific term, but the first implementation maps that abstraction to RAGFlow datasets.

For the MVP, the Platform does not create RAGFlow datasets or proxy document upload. Operators manage documents and parsing settings in RAGFlow. The Platform connects to RAGFlow, syncs or registers datasets as Knowledge Sources, lets Job Templates bind those sources, and uses the Knowledge Adapter at runtime.

The MVP supports one active RAGFlow Knowledge Connection. The data model may keep a `connection_id` so multiple providers or multiple RAGFlow instances can be added later, but the admin UI and business rules should treat the active connection as singular.

RAGFlow dataset sync is manual in the MVP. New external datasets are discovered as unregistered candidates; registered Knowledge Sources are refreshed with external metadata; missing datasets are marked as missing rather than deleted. If a missing Knowledge Source is bound to a Job Template, the admin UI must surface the risk before publishing.

At runtime, missing Knowledge Sources are skipped rather than unbound or deleted. If some authorized sources are available, retrieval continues and the response includes warnings for unavailable sources. If all authorized sources are unavailable, Platform returns a `knowledge_sources_unavailable` error with an audit ID.

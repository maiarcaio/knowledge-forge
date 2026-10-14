# Privacy and platform boundaries

Knowledge Forge is designed for one local user. Raw transcripts, exports, and source metadata remain under `data/` on the Mac unless the user explicitly configures an AI provider.

When cloud AI is configured, only the retrieved evidence chunks and the current question are sent to that provider. Do not send the entire library by default.

The project must not collect passwords, browser cookies, private API traffic, private/paid media, or social-account session tokens. It does not bypass access controls. Instagram saved-content synchronization is out of scope until a separate opt-in feasibility report confirms a lawful, stable method.

YouTube caption ingestion uses public caption availability. A source with no accessible captions is marked `captions_unavailable`; it is not fabricated or silently summarized.

<script lang="ts">
  import { page } from '$app/stores'
  import { ingestFile, streamQuery, type ChatMessage, type Citation } from '$lib/api'

  const kbId = $derived($page.params.id)

  let messages  = $state<ChatMessage[]>([])
  let question  = $state('')
  let uploading = $state(false)
  let querying  = $state(false)
  let fileInput = $state<HTMLInputElement | null>(null)

  async function handleUpload(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    uploading = true
    try {
      const res = await ingestFile(kbId, file)
      messages = [...messages, {
        role: 'ai',
        content: `✓ Ingested **${file.name}** — ${res.chunks_stored} chunks stored.`
      }]
    } catch {
      messages = [...messages, { role: 'ai', content: '✗ Upload failed.' }]
    } finally {
      uploading = false
      if (fileInput) fileInput.value = ''
    }
  }

  async function send() {
    if (!question.trim() || querying) return

    const q = question.trim()
    question = ''

    // push user message and an empty AI bubble
    messages = [...messages, { role: 'human', content: q }]
    messages = [...messages, { role: 'ai', content: '', citations: [] }]
    const aiIdx = messages.length - 1

    querying = true
    try {
      const history = messages
        .slice(0, -2)                     // exclude the current pair
        .map(m => ({ role: m.role, content: m.content }))

      for await (const chunk of streamQuery(kbId, q, history)) {
        if (chunk.type === 'token') {
          // mutate the last message's content in place — Svelte 5 tracks this
          messages[aiIdx] = {
            ...messages[aiIdx],
            content: messages[aiIdx].content + chunk.text
          }
        } else {
          messages[aiIdx] = { ...messages[aiIdx], citations: chunk.data }
        }
      }
    } catch {
      messages[aiIdx] = { ...messages[aiIdx], content: 'Error — could not reach the API.' }
    } finally {
      querying = false
    }
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }
</script>

<main>
  <header>
    <a href="/">← back</a>
    <span class="kb-id">KB: {kbId}</span>
    <label class="upload-btn">
      {uploading ? 'Uploading…' : 'Upload file'}
      <input
        type="file"
        bind:this={fileInput}
        accept=".pdf,.docx,.txt,.md"
        onchange={handleUpload}
        disabled={uploading}
        hidden
      />
    </label>
  </header>

  <div class="messages">
    {#each messages as msg (msg)}
      <div class="msg {msg.role}">
        <p>{msg.content}</p>
        {#if msg.citations && msg.citations.length > 0}
          <details class="citations">
            <summary>{msg.citations.length} source{msg.citations.length > 1 ? 's' : ''}</summary>
            {#each msg.citations as c}
              <div class="citation">
                <span class="source">{c.source}{c.page != null ? ` · p.${c.page}` : ''}</span>
                <p class="chunk">{c.chunk}</p>
              </div>
            {/each}
          </details>
        {/if}
      </div>
    {/each}

    {#if querying}
      <div class="msg ai thinking">thinking…</div>
    {/if}
  </div>

  <div class="input-row">
    <textarea
      bind:value={question}
      onkeydown={onKey}
      placeholder="Ask a question… (Enter to send)"
      rows="2"
      disabled={querying}
    ></textarea>
    <button onclick={send} disabled={!question.trim() || querying}>Send</button>
  </div>
</main>

<style>
  main          { max-width: 720px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; padding: 0 1rem; font-family: sans-serif; }
  header        { display: flex; align-items: center; gap: 1rem; padding: .75rem 0; border-bottom: 1px solid #eee; }
  a             { color: #2563eb; text-decoration: none; font-size: .9rem; }
  .kb-id        { color: #888; font-size: .85rem; flex: 1; }
  .upload-btn   { padding: .4rem .8rem; background: #f3f4f6; border: 1px solid #ddd; border-radius: 6px; cursor: pointer; font-size: .85rem; }
  .messages     { flex: 1; overflow-y: auto; padding: 1rem 0; display: flex; flex-direction: column; gap: .75rem; }
  .msg          { max-width: 85%; padding: .75rem 1rem; border-radius: 10px; line-height: 1.5; }
  .msg p        { margin: 0; white-space: pre-wrap; }
  .human        { background: #2563eb; color: #fff; align-self: flex-end; }
  .ai           { background: #f3f4f6; color: #111; align-self: flex-start; }
  .thinking     { color: #888; font-style: italic; }
  .citations    { margin-top: .5rem; font-size: .8rem; }
  summary       { cursor: pointer; color: #2563eb; }
  .citation     { margin-top: .5rem; padding: .5rem; background: #fff; border-radius: 6px; border: 1px solid #e5e7eb; }
  .source       { font-weight: 600; color: #374151; }
  .chunk        { margin: .25rem 0 0; color: #6b7280; font-size: .75rem; line-height: 1.4; }
  .input-row    { display: flex; gap: .5rem; padding: .75rem 0; border-top: 1px solid #eee; }
  textarea      { flex: 1; padding: .5rem .75rem; border: 1px solid #ddd; border-radius: 6px; font-size: .9rem; resize: none; font-family: inherit; }
  button        { padding: .5rem 1rem; background: #2563eb; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
  button:disabled { opacity: .4; cursor: default; }
</style>
<script lang="ts">
  import { onMount } from 'svelte'
  import { listKBs, createKB, deleteKB, type KnowledgeBase } from '$lib/api'

  let kbs     = $state<KnowledgeBase[]>([])
  let name    = $state('')
  let desc    = $state('')
  let loading = $state(true)
  let error   = $state('')

  async function load() {
    try { kbs = await listKBs() }
    catch { error = 'Could not load knowledge bases' }
    finally { loading = false }
  }

  async function create() {
    if (!name.trim()) return
    const kb = await createKB(name.trim(), desc.trim() || undefined)
    kbs = [...kbs, kb]
    name = ''
    desc = ''
  }

  async function remove(id: string) {
    await deleteKB(id)
    kbs = kbs.filter(k => k.id !== id)
  }

  onMount(load)
</script>

<main>
  <h1>ragbase</h1>

  <section class="create">
    <input bind:value={name} placeholder="Knowledge base name" />
    <input bind:value={desc} placeholder="Description (optional)" />
    <button onclick={create} disabled={!name.trim()}>Create</button>
  </section>

  {#if loading}
    <p class="muted">Loading…</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if kbs.length === 0}
    <p class="muted">No knowledge bases yet. Create one above.</p>
  {:else}
    <ul class="kb-list">
      {#each kbs as kb (kb.id)}
        <li>
          <a href="/kb/{kb.id}">
            <span class="kb-name">{kb.name}</span>
            {#if kb.description}<span class="muted">{kb.description}</span>{/if}
          </a>
          <button class="danger" onclick={() => remove(kb.id)}>Delete</button>
        </li>
      {/each}
    </ul>
  {/if}
</main>

<style>
  main        { max-width: 640px; margin: 4rem auto; padding: 0 1rem; font-family: sans-serif; }
  h1          { font-size: 1.5rem; margin-bottom: 2rem; }
  .create     { display: flex; gap: .5rem; margin-bottom: 2rem; }
  input       { flex: 1; padding: .5rem .75rem; border: 1px solid #ddd; border-radius: 6px; font-size: .9rem; }
  button      { padding: .5rem 1rem; border: none; border-radius: 6px; cursor: pointer; background: #2563eb; color: #fff; font-size: .9rem; }
  button:disabled { opacity: .4; cursor: default; }
  button.danger   { background: transparent; color: #dc2626; font-size: .8rem; }
  .kb-list    { list-style: none; padding: 0; display: flex; flex-direction: column; gap: .5rem; }
  li          { display: flex; align-items: center; justify-content: space-between; padding: .75rem 1rem; border: 1px solid #eee; border-radius: 8px; }
  a           { text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: .2rem; }
  .kb-name    { font-weight: 500; }
  .muted      { color: #888; font-size: .85rem; }
  .error      { color: #dc2626; }
</style>
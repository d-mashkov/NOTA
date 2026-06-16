// ============================================
// Supabase Client — NOTA
// Замени URL и ANON_KEY на свои из Supabase Dashboard
// Project Settings → API
// ============================================

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';

const SUPABASE_URL  = 'https://tybhcaniptpokuislvdj.supabase.co';
const SUPABASE_ANON = 'sb_publishable_riZvglJDb1ytK90cH1a9ig_b-92pf4s';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);

// ---- Хелперы авторизации ----

export async function getSession() {
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}

export async function requireAuth() {
  // Auth временно отключена
  return true;
}

export async function getCurrentUser() {
  // Auth временно отключена — возвращаем дефолтного пользователя
  return {
    email: 'dmashkovjob@gmail.com',
    name: 'Denis',
    role: 'admin',
  };
}

export async function signOut() {
  await supabase.auth.signOut();
  window.location.href = 'login.html';
}

// ---- Хелперы данных ----

export async function getNotes(filters = {}) {
  let query = supabase
    .from('notes')
    .select(`*, categories(name), note_reports(ai_output, ai_recommendation)`)
    .in('status', ['published', 'pending'])
    .order('created_at', { ascending: false });

  if (filters.category) query = query.eq('category_id', filters.category);
  if (filters.recommendation) query = query.eq('recommendation', filters.recommendation);
  if (filters.trend_stage) query = query.eq('trend_stage', filters.trend_stage);

  const { data, error } = await query;
  return { data, error };
}

export async function getNoteById(id) {
  const { data, error } = await supabase
    .from('notes')
    .select(`*, categories(name), note_reports(*), note_comments(*, users(name))`)
    .eq('id', id)
    .single();
  return { data, error };
}

export async function addComment(noteId, userId, text) {
  const { data, error } = await supabase
    .from('note_comments')
    .insert({ note_id: noteId, user_id: userId, text });
  return { data, error };
}

export async function saveNote(userId, noteId) {
  const { data, error } = await supabase
    .from('saved_notes')
    .upsert({ user_id: userId, note_id: noteId });
  return { data, error };
}

export async function unsaveNote(userId, noteId) {
  const { error } = await supabase
    .from('saved_notes')
    .delete()
    .eq('user_id', userId)
    .eq('note_id', noteId);
  return { error };
}

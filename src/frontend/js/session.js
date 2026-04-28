/**
 * session.js — Estado de sesión compartido entre páginas
 * Proyecto: StockPulse
 *
 * Usa sessionStorage para mantener el token entre páginas.
 * Se pierde al cerrar la pestaña/navegador (comportamiento deseado).
 */
 
const API_BASE = 'http://localhost:8000';
 
const session = {
  get token()     { return sessionStorage.getItem('sp_token'); },
  set token(v)    { v ? sessionStorage.setItem('sp_token', v) : sessionStorage.removeItem('sp_token'); },
  get username()  { return sessionStorage.getItem('sp_username'); },
  set username(v) { v ? sessionStorage.setItem('sp_username', v) : sessionStorage.removeItem('sp_username'); },
  isLoggedIn()    { return !!sessionStorage.getItem('sp_token'); },
  clear()         { sessionStorage.removeItem('sp_token'); sessionStorage.removeItem('sp_username'); }
};
 
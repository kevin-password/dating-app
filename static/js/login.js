(function () {
  const username = document.getElementById('id_username');
  const password = document.getElementById('id_password');
  const submitBtn = document.getElementById('submitBtn');
  const emailHint = document.getElementById('emailHint');
  const togglePwd = document.getElementById('togglePwd');

  if (!username || !password) return;

  function looksLikeEmail(v){ return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }

  function validate(){
    const u = username.value.trim();
    const p = password.value;
    submitBtn.disabled = !(u.length >= 2 && p.length >= 4);
    emailHint.style.display = looksLikeEmail(u) ? 'block' : 'none';
  }

  username.addEventListener('input', validate);
  password.addEventListener('input', validate);

  togglePwd?.addEventListener('click', function(){
    if (password.type === 'password') {
      password.type = 'text';
      this.textContent = 'Hide';
    } else {
      password.type = 'password';
      this.textContent = 'Show';
    }
    password.focus();
  });

  validate();
})();

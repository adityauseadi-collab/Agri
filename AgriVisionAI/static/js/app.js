/**
 * AgriVision AI – Global JS utilities
 */

// ── Auto-dismiss flash alerts after 4 s ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.fade.show').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    });
  }, 4000);
});

// ── Smooth number counter animation for stat cards ───────────────────────────
function animateCounter(el, target, duration) {
  const start = performance.now();
  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.textContent = Math.round(eased * target);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.stat-value').forEach(function (el) {
    const val = parseInt(el.textContent, 10);
    if (!isNaN(val) && val > 0) {
      el.textContent = '0';
      const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCounter(el, val, 700);
            observer.disconnect();
          }
        });
      });
      observer.observe(el);
    }
  });
});

// ── Confirm helper (used in delete buttons) ──────────────────────────────────
function agriConfirm(message) {
  return window.confirm(message);
}

// ── Toast notification helper ────────────────────────────────────────────────
function showToast(message, type) {
  type = type || 'success';
  const colorMap = {
    success: { bg: '#E8F5E9', color: '#1B5E20', icon: 'bi-check-circle-fill' },
    danger:  { bg: '#FFEBEE', color: '#c62828', icon: 'bi-x-circle-fill' },
    info:    { bg: '#E3F2FD', color: '#1565C0', icon: 'bi-info-circle-fill' },
    warning: { bg: '#FFF8E1', color: '#E65100', icon: 'bi-exclamation-triangle-fill' },
  };
  const c = colorMap[type] || colorMap.success;

  const toast = document.createElement('div');
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:${c.bg};color:${c.color};border:1.5px solid ${c.color}33;
    border-radius:12px;padding:12px 18px;
    box-shadow:0 8px 24px rgba(0,0,0,.12);
    display:flex;align-items:center;gap:10px;
    font-size:.88rem;font-weight:500;
    animation:slideInRight .3s ease both;
    max-width:320px;
  `;
  toast.innerHTML = `<i class="bi ${c.icon}" style="font-size:1rem"></i>${message}`;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideOutRight .3s ease both';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Inject toast keyframes once
const toastStyle = document.createElement('style');
toastStyle.textContent = `
  @keyframes slideInRight {
    from { opacity:0; transform:translateX(20px); }
    to   { opacity:1; transform:translateX(0); }
  }
  @keyframes slideOutRight {
    from { opacity:1; transform:translateX(0); }
    to   { opacity:0; transform:translateX(20px); }
  }
`;
document.head.appendChild(toastStyle);

// ── Active nav link highlighting ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-link').forEach(function (link) {
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });
});

// ── Print-friendly helper ────────────────────────────────────────────────────
function printSection(sectionId) {
  const el = document.getElementById(sectionId);
  if (!el) return;
  const win = window.open('', '_blank');
  win.document.write(`
    <html><head>
      <title>AgriVision AI – Report</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"/>
      <style>body{padding:24px;font-family:Inter,sans-serif}</style>
    </head><body>${el.innerHTML}</body></html>
  `);
  win.document.close();
  win.print();
}

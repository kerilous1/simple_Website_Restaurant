/**
 * main.js — Kero Restaurant global client-side behaviour
 * ========================================================
 *
 * Responsibilities:
 *   1. Auto-dismiss flash/alert messages after 5 seconds.
 *   2. Validate quantity inputs — enforce a minimum of 1.
 *   3. Lazy-load images via IntersectionObserver (progressive enhancement).
 *
 * All handlers are registered after DOMContentLoaded.
 * No external libraries required.
 */

document.addEventListener('DOMContentLoaded', function () {

    // ------------------------------------------------------------------
    // 1. Auto-dismiss alert / flash messages
    // ------------------------------------------------------------------
    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(function () {
                if (alert.parentNode) alert.parentNode.removeChild(alert);
            }, 400);
        }, 5000);
    });

    // ------------------------------------------------------------------
    // 2. Quantity input guard — prevent values below 1
    //    Bug fix: was comparing DOM string to number without parseInt()
    // ------------------------------------------------------------------
    document.querySelectorAll('.quantity-input').forEach(function (input) {
        input.addEventListener('change', function () {
            var val = parseInt(this.value, 10);
            if (isNaN(val) || val < 1) {
                this.value = 1;
            }
        });
    });

    // ------------------------------------------------------------------
    // 3. Lazy image loading via IntersectionObserver
    //    Falls back gracefully in browsers that do not support the API.
    // ------------------------------------------------------------------
    if ('IntersectionObserver' in window) {
        var lazyImages = document.querySelectorAll('img.lazy');
        if (lazyImages.length > 0) {
            var observer = new IntersectionObserver(function (entries, obs) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        var img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        obs.unobserve(img);
                    }
                });
            });
            lazyImages.forEach(function (img) { observer.observe(img); });
        }
    }

});
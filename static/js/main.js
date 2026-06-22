/**
 * Print Village Main UI Scripts
 * Handles scrolling effects, toast alerts auto-dismissal,
 * dynamic glassmorphism updates, and micro-interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Sticky Header scroll effects
    const nav = document.getElementById('mainNav');
    if (nav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                nav.classList.add('navbar-scrolled');
            } else {
                nav.classList.remove('navbar-scrolled');
            }
        });
    }

    // 2. Auto-dismiss Toast notifications after 5 seconds
    const toastElements = document.querySelectorAll('.toast');
    toastElements.forEach(toastEl => {
        setTimeout(() => {
            const bsToast = bootstrap.Toast.getInstance(toastEl);
            if (bsToast) {
                bsToast.hide();
            } else {
                // fallback if bootstrap instance not initialized yet
                const toast = new bootstrap.Toast(toastEl);
                toast.hide();
            }
        }, 5000);
    });

    // 3. Simple scroll reveal animations for elements with class 'reveal'
    const revealElements = document.querySelectorAll('.reveal');
    const revealOnScroll = () => {
        const triggerBottom = window.innerHeight * 0.85;
        revealElements.forEach(el => {
            const elTop = el.getBoundingClientRect().top;
            if (elTop < triggerBottom) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });
    };
    
    if (revealElements.length > 0) {
        window.addEventListener('scroll', revealOnScroll);
        revealOnScroll(); // Initial invocation
    }
});

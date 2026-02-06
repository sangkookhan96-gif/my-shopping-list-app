/**
 * 한상국의 쉬운 중국경제뉴스 해설 - Main JavaScript
 * Vanilla JS for original content toggle functionality
 */

(function() {
    'use strict';

    /**
     * Initialize all toggle buttons for original content
     */
    function initToggleButtons() {
        const toggleButtons = document.querySelectorAll('.toggle-original-btn');

        toggleButtons.forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('data-target');
                const target = document.getElementById(targetId);

                if (target) {
                    const isCollapsed = target.classList.contains('collapsed');

                    if (isCollapsed) {
                        // Expand
                        target.classList.remove('collapsed');
                        this.classList.add('expanded');
                        this.textContent = '원문 접기';

                        // Scroll into view if needed
                        setTimeout(function() {
                            const rect = target.getBoundingClientRect();
                            if (rect.bottom > window.innerHeight) {
                                target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }
                        }, 100);
                    } else {
                        // Collapse
                        target.classList.add('collapsed');
                        this.classList.remove('expanded');
                        this.textContent = '원문 보기';
                    }
                }
            });
        });
    }

    /**
     * Initialize collapse buttons inside original content
     */
    function initCollapseButtons() {
        const collapseButtons = document.querySelectorAll('.collapse-btn');

        collapseButtons.forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const originalContent = this.closest('.original-content');

                if (originalContent) {
                    // Find the toggle button for this content
                    const contentId = originalContent.id;
                    const toggleBtn = document.querySelector('[data-target="' + contentId + '"]');

                    // Collapse the content
                    originalContent.classList.add('collapsed');

                    // Update toggle button state
                    if (toggleBtn) {
                        toggleBtn.classList.remove('expanded');
                        toggleBtn.textContent = '원문 보기';

                        // Scroll toggle button into view
                        toggleBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            });
        });
    }

    /**
     * Add smooth scrolling for anchor links
     */
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
            anchor.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href');
                if (targetId && targetId !== '#') {
                    const target = document.querySelector(targetId);
                    if (target) {
                        e.preventDefault();
                        target.scrollIntoView({ behavior: 'smooth' });
                    }
                }
            });
        });
    }

    /**
     * Add keyboard navigation support
     */
    function initKeyboardNav() {
        document.addEventListener('keydown', function(e) {
            // ESC key closes expanded original content
            if (e.key === 'Escape') {
                const expandedContents = document.querySelectorAll('.original-content:not(.collapsed)');
                expandedContents.forEach(function(content) {
                    const collapseBtn = content.querySelector('.collapse-btn');
                    if (collapseBtn) {
                        collapseBtn.click();
                    }
                });
            }
        });
    }

    /**
     * Initialize intro card (show once for first visit, then hide)
     */
    function initIntroCard() {
        var STORAGE_KEY = 'intro_card_dismissed';
        var card = document.getElementById('introCard');
        var closeBtn = document.getElementById('introCardClose');

        if (!card) return;

        if (localStorage.getItem(STORAGE_KEY)) {
            card.classList.add('hidden');
            return;
        }

        closeBtn.addEventListener('click', function() {
            card.classList.add('hidden');
            localStorage.setItem(STORAGE_KEY, '1');
        });
    }

    /**
     * Initialize on DOM ready
     */
    function init() {
        initToggleButtons();
        initCollapseButtons();
        initSmoothScroll();
        initKeyboardNav();
        initIntroCard();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

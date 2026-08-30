// Mundana 主题交互(原生JS,无jQuery依赖)
(function () {
    // 导航栏:下滑隐藏,上滑显示
    var nav = document.querySelector('nav.topnav');
    if (nav) {
        var lastY = window.scrollY, ticking = false;
        var update = function () {
            var y = window.scrollY;
            if (Math.abs(y - lastY) > 5) {
                if (y > lastY && y > nav.offsetHeight) {
                    nav.style.top = -nav.offsetHeight + 'px';
                } else if (y + window.innerHeight < document.documentElement.scrollHeight) {
                    nav.style.top = '0px';
                }
                lastY = y;
            }
            ticking = false;
        };
        window.addEventListener('scroll', function () {
            if (!ticking) {
                ticking = true;
                requestAnimationFrame(update);
            }
        });
    }
})();

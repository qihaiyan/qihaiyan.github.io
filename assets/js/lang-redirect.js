// 非中文浏览器自动切换到英文版；用户点过"中文版"后本次会话不再跳转。
// 目标 URL 由页面注入(window.langAlt,见 _layouts/default.html)。
// 独立成文件的原因:内联在 HTML 里时,AI Search 的静态爬虫会把
// location.replace 识别为重定向声明,把英文页内容存到中文 URL 名下,
// 导致中文文章从搜索索引中消失。
(function () {
    try {
        if (!window.langAlt) return;
        var nav = (navigator.language || navigator.userLanguage || 'zh').toLowerCase();
        if (nav.indexOf('zh') !== 0 && sessionStorage.getItem('langChoice') !== 'zh') {
            location.replace(window.langAlt);
        }
    } catch (e) { }
})();

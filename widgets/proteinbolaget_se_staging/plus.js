document.getElementById('betyg')?.insertAdjacentHTML('afterend', '<div id="testfreaks-reviews"></div>');
document.getElementById('OrderFalt')?.insertAdjacentHTML('afterend', '<div id="testfreaks-badge"></div>');

testFreaks = window.testFreaks || [];
testFreaks.push(["load", ["badge", "reviews"]]);

(function (d, t, p) { var e = d.createElement(t); e.charset = "utf-8"; e.src = p; var s = d.getElementsByTagName(t)[0]; s.parentNode.insertBefore(e, s) })(document, "script", "https://admin.testfreaks.com/admin/widget_script/2621/test");


var sortSVG = document.querySelector(".icon icon-xs bg-base-1")
var sortDiv = document.querySelector(".pull-left:not(role)")
sortDiv.appendChild(sortSVG)
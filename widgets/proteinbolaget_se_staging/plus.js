document.getElementById('betyg')?.insertAdjacentHTML('afterend', '<div id="testfreaks-reviews"></div>');
document.getElementById('OrderFalt')?.insertAdjacentHTML('afterend', '<div id="testfreaks-badge"></div>');

testFreaks = window.testFreaks || [];
testFreaks.push(["load", ["badge", "reviews"]]);

(function (d, t, p) { var e = d.createElement(t); e.charset = "utf-8"; e.src = p; var s = d.getElementsByTagName(t)[0]; s.parentNode.insertBefore(e, s) })(document, "script", "https://admin.testfreaks.com/admin/widget_script/2621/test");

// (function (d, t, p) { var e = d.createElement(t); e.charset = "utf-8"; e.src = p; var s = d.getElementsByTagName(t)[0]; s.parentNode.insertBefore(e, s) })(document, "script", "https://js.testfreaks.com/onpage/oriflame-se-sv/reviews.json?key=46989");


// var sortSVG = document.querySelector(".icon icon-xs bg-base-1")
// var sortDiv = document.querySelector(".pull-left:not(role)")
// sortDiv.appendChild(sortSVG)

// var score = reviews[0]reviews[_]['score'];
// var divScore = div("tf-grade", { text: score + " av 5" })
// var divScoreByDoc = r.querySelector(".score .hcol")
// console.log(divScoreByDoc)
// divScoreByDoc.appendChild(divScore)

var r = document.querySelector("hrow");
var divHrow = r.querySelector(".hrow");
var parent = r.querySelector(".header");
parent.appendChild(divHrow)

  var tdStars = document.querySelectorAll("td.sym")
  forEach(tdStars, function(_, star) {
    star.innerHTML = '⭐';

    console.log("star=", star)
  });
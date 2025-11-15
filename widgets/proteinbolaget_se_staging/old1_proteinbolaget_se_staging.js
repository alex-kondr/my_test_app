(function() {
  //= require widget
  var w = testFreaks.widget, e = testFreaks.element, div = e.curry("div"), forEach = testFreaks.forEach, t = testFreaks.translate;
  w.setCss("%=stylesheet");
  w.setEnableWriteReview(false);
  w.setCssAttr("distribution-color-star", "#222222");
  w.setTranslations({ basedon: "%=t %d reviews" });
  testFreaks.options.set("showSortThreshold", 1);
  testFreaks.options.set("showProductName", true);
  
  w.setEnableVerifiedBuyer(true);
  
  w.setOptions({ onReviews: onReviews });
  w.setOptions({ onData: onData });
  
  function onData(data) {
    console.log(data);
  }

  function onReviews(reviews) {
    console.log(reviews);
    
    var revs = document.querySelectorAll(".testfreaks-reviews .customer-review:not(.upd)");
    forEach(revs, function(_, r) {
      r.classList.add('upd');
      
      var divHrow = r.querySelector(".hrow");
      var parent = r.querySelector(".header");
      parent.appendChild(divHrow)
      
      var score = reviews["reviews"][_]["score"];
      var divScore = div("tf-grade", { text: score + " av 5"});
      var divHcol = r.querySelector(".score.hcol")
      divHcol.appendChild(divScore);
      
      var divExtract = r.querySelector(".content .extract");
      var prodName = r.querySelector(".footer .product-name");
      divExtract.appendChild(prodName);
    });
  };

  testFreaks.options.set("showTabCounts", false);

  // w.setApiClientName("oriflame-se-sv");
  // w.setProductId("42495");
  w.setApiClientName("mio.se");
  w.setProductId("M2240259");
  
  w.run();
})();

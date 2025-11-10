(function() {
  //= require widget
  var w = testFreaks.widget, e = testFreaks.element, div = e.curry("div"), forEach = testFreaks.forEach, t = testFreaks.translate;
  w.setCss("%=stylesheet");
  w.setEnableWriteReview(false);
  w.setCssAttr("distribution-color-star", "#000");
  w.setTranslations({ basedon: "%=t %d reviews" });
  w.setTranslations({ verified_buyer: "%=t Verified"});
  // w.setTranslations({ review_tab: "%=t Rating" });
  testFreaks.options.set("showSortThreshold", 1);
  
  w.setEnableVerifiedBuyer(true);
  
  w.setOptions({ onReviews: onReviews });
  w.setOptions({ onData: onData });
  
  function onData(data) {
    console.log(data);
  }
  
  function onReviews(reviews) {
    console.log(reviews);
    
    // var revs = document.querySelectorAll(".testfreaks .article:not(.upd)");
    var revs = document.querySelectorAll(".customer-review:not(.upd)");
    // console.log('revs=', revs)
    forEach(revs, function(_, r) {
      r.classList.add('upd');
      // r.setAttribute("style", "display: flex !important;")
      // console.log('r=', r);
      // var logo = r.querySelector(".text-logo");
      // logo.setAttribute("style", "display: none !important");

      // var footer = r.querySelector(".footer")
      // footer.setAttribute("style", "display: none !important");
      
      // var time = r.querySelector("time");
      // time.setAttribute("style", "display: none !important");
      
      // var divHrows = r.querySelectorAll(".hrow");
      // forEach(divHrows, function(_, divHrow) {
      //   divHrow.setAttribute("style", "margin-left: 0px !important; display: flex !important;");
        
      //   var span = divHrow.querySelector("span");
      //   if (span) {
      //     span.setAttribute("style", "display: none !important");
      //   };
      // });
      
      var divHrow = r.querySelector(".hrow");
      var parent = r.querySelector(".header");
      parent.appendChild(divHrow)
      
      var score = reviews["reviews"][_]["score"];
      var divScore = div("tf-grade", { text: score + " av 5"}); //, style: "margin-left: .5em !important;" 
      var divHcol = r.querySelector(".score.hcol")
      divHcol.appendChild(divScore);
      
      // var content = r.querySelector(".content");
      // content.setAttribute("style", "margin-left: 0px !important");
      
    });
  };

  testFreaks.options.set("showTabCounts", false);

  w.setApiClientName("oriflame-se-sv");
  w.setProductId("42495");
  
  w.run();
})();

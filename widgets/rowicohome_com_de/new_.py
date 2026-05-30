(function() {
  //= require widget
  testFreaks.options.set("customDateFormat", "de-DE");
  //= require rowicohome_com_sv_render_v2
  testFreaks.addTranslations({badge: "(%d)"});

  var w = testFreaks.widget, e = testFreaks.element, div = e.curry("div"), noticeReviews = false;
  w.setCss("%=stylesheet");
  w.setEnableWriteReview(false);
  w.setCssAttr("svg-star-color", "#2d2d2d");
//  w.setCssAttr("tabs-selected-border-color", "#222222");
//  w.setCssAttr("distribution-color", "#222222");
  w.setCssAttr("distribution-color-star", "#646464");
  w.setCssAttr("svg-verified-color", "#747869");
  w.setCssAttr("svg-more-color", "#2D2D2D");
  w.setEnablePoweredBy(false);
  w.setEnableVerifiedBuyer(true);
  w.setOptions({ onReviews: createNotice });
  w.setTranslations({
    review_questions: {
/*      fit3: {
        review: "Passform:",
        short: "Passform:",
        summary: "Upplevd passform",
        options: {
          "small": {review: "Liten", summary: "Liten"},
          "normal": {review: "Perfekt", summary: "Perfekt"},
          "large": {review: "Stor", summary: "Stor"}
        }
      },
      size: {
        review: "Köpt storlek:",
      },
      color: {
        review: "Färg:",
      },
*/
      color: {
        review: "Gekaufte Variante:",
      },
    }
  });
  
  function createNotice(reviews, $) {
    if (!noticeReviews && jQuery(".testfreaks-reviews > .testfreaks").length) {
      jQuery(".testfreaks-reviews > .testfreaks").append("<div class='tf-notice'><p>Alle Bewertungen stammen von verifizierten Käufern, die das Produkt bei Rowico Home erworben haben, und die Bewertungen werden von <a href='https://trustvoice.com/products/' target='_blank'>Trustvoice</a> verwaltet.</p></div>");
      noticeReviews = true;
    }
  }

  var renderAISummary = testFreaks.render.aiSummary;
  testFreaks.render.aiSummary = function(aiSummaryData, productData, opts) {
    var aiSummary = renderAISummary(aiSummaryData, productData, opts)
    var heading = aiSummary.querySelector('.heading');
    var stars = aiSummary.querySelector('.tf-stars-svg');
    var ratingDiv = div("tf-rating-wrapper");
    var revsCount = div("tf-count tf-link tf-linkable", { text: "(" + productData.your_review_count + ")"});

    ratingDiv.appendChild(stars);
    ratingDiv.appendChild(revsCount);
    heading.appendChild(ratingDiv)

    return aiSummary;
  }
  
  w.setApiClientName("rowicohome.com-de");
  w.setProductId("119834");
  
  w.run();
})();


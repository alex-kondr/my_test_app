(function () {
    //= require widget
    var w = testFreaks.widget, e = testFreaks.element, div = e.curry("div"), forEach = testFreaks.forEach, t = testFreaks.translate;
    w.setCss("%=stylesheet");
    w.setEnableWriteReview(false);
    w.setCssAttr("distribution-color-star", "#000");
    w.setTranslations({ basedon: "%=t %d reviews" });
    w.setTranslations({ verified_buyer: "%=t Verified" });
    // w.setTranslations({ review_tab: "%=t Rating" });
    testFreaks.options.set("showSortThreshold", 1);

    w.setEnableVerifiedBuyer(true);

    w.setOptions({ onReviews: onReviews })
    w.setOptions({ onData: onData })

    function onData(data) {
        console.log(data);
    }

    function onReviews(reviews) {
        console.log(reviews);

        var revs = document.querySelectorAll(".testfreaks .article:not(.upd)");
        forEach(revs, function (_, r) {
            // r.classList.add('upd');

            // var score = reviews[0]reviews[_]['score'];

            // var divScore = div("tf-grade", {text: ""})


        });
    };

    // testFreaks.options.set("showTabCounts", false);

    w.setApiClientName("oriflame-se-sv");
    w.setProductId("42495");

    w.run();
})();

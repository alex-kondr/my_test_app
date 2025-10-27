var revs = document.querySelectorAll(".customer-review");

revs.forEach(rev => {
    var logo = rev.querySelector(".text-logo");
    logo.setAttribute("style", "display: none !important");

    var verified = rev.querySelector(".verified");
    verified.setAttribute("style", "display: none !important");

    var divStars = rev.querySelector(".score")
    divStars.setAttribute("style", "float: right !important");
    rev.prepend(divStars);

    var divHrow = rev.querySelector(".hrow");
    divHrow.setAttribute("style", "margin-left: 0px !important; display: flex !important; flex-direction: column !important");

    spans = divHrow.querySelectorAll("span");
    spans.forEach(span => {
        span.setAttribute("style", "display: none !important");
    })

    divContent = rev.querySelector(".content");
    divContent.setAttribute("style", "margin-left: 0px !important");
})


var distributionRow = document.querySelector(".tf-distribution").querySelectorAll("tr")
distributionRow.forEach(tr => {
    var count = tr.querySelector(".bar").title.split("/")[0]

    var countTd = document.createElement("td")
    countTd.classList.add("count")
    countTd.innerHTML = count

    tr.appendChild(countTd)

})


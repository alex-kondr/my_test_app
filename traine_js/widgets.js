var revs = document.querySelectorAll(".customer-review")

revs.forEach(rev => {
    var logo = rev.querySelector(".text-logo");
    var verified = rev.querySelector(".verified");
    logo.remove();
    verified.remove();

    var divStars = rev.querySelector(".score")
    divStars.classList.add("pull-right")
    rev.prepend(divStars);

    var divHrow = rev.querySelector(".hrow");
    divHrow.classList.add("pull-left");
    divHrow.classList.remove("hrow");
})


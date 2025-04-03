// document.getElementById("count-el").innerText = 6

let count = 0

let countEl = document.getElementById("count-el")

// console.log(count)

// let myAge = 36
// console.log(myAge)

function increment() {
    count = count + 1
    countEl.innerText = count
}

hehe = 1;
curind = 0;

function bclick() {
    document.getElementsByClassName("tempdisplay")[0].style.display="none";
    startTests();
}

function why() {
    $('.test'+ hehe).remove();
    hehe += 1;
    curind += 1;
    $("#includedContent").load("test_" + hehe + ".html");
}


w = window.innerWidth
setInterval(() => {
    if (Math.abs(window.innerWidth - w) > 200) {
        textbox = document.getElementsByClassName("tempdisplay")[0];
        textbox.style.display="block";
        textbox.getElementsByClassName('error')[0].textContent = "Do not resize or rotate the window or device while doing tests. This will invalidate the validity of the test.\nPlease reload the webpage to continue.\n\n進行測試時請勿調整視窗或設備的大小或旋轉視窗或設備。這將使測試的有效性失效。請重新加載網頁以繼續。";
        textbox.getElementsByClassName("yea")[0].textContent = "Reload";
        textbox.getElementsByClassName("yea")[0].onclick = function() { location.reload(); };
    }
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight * 0.7;
    fixsize();
});


st = "";
testdata = [[], [], [], [], []]
startTimes = []
function startTests() {
    startTimes.put(Date.now());
}
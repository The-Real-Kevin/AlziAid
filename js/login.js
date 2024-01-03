function encryptPassword(password) {
    // encrpytion L
    return password;
}


function loginn() {
    document.getElementById("error").innerHTML = "";
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const encryptedPassword = encryptPassword(password);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "https://expsrv.isf.edu.hk/login", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                document.cookie = "session=" + xhr.responseText;
                alert("Login successful!");
            } else {
                document.getElementById("error").innerHTML = "This password is incorrect.";
                document.getElementById("username").value = "";
                document.getElementById("password").value = "";
            }
        }
    };
    xhr.send(JSON.stringify({ username, password: encryptedPassword }));
}

function showPopup() {
    var popup = document.getElementById("popup");
    popup.style.display = 'block';
    document.getElementById("forgot_text").onclick = "";
}

function showPopup2() {
    var popup = document.getElementById("popup");
    popup.remove();
    var popup = document.getElementById("popup2");
    popup.style.display = 'block';
}
function resett() {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "https://expsrv.isf.edu.hk/auth/forgot", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                showPopup2();
            } else {
                showPopup2();
            }
        } else {
            showPopup2();
        }
    };
    xhr.send(JSON.stringify({ username }));
}
function do_verify() {
    const sessionCookie = document.cookie.split(';').find(cookie => cookie.startsWith('session='));
    if (sessionCookie) {
        const sessionId = sessionCookie.split('=')[1];
        const checkSessionUrl = `https://expsrv.isf.edu.hk/auth/checksession?id=${sessionId}`;
        fetch(checkSessionUrl)
            .then(response => response.json())
            .then(data => {
                if (data === true) {
                    window.location.href = './../home.html';
                }
            })
            .catch(error => { });
    } else {
        window.location.href = './../login.html';
    }
}
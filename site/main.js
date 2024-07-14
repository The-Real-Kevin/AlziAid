
hehe = 1;
curind = 0;

titles = ['Saccadic Movement', 'Anti-Saccadic Movement', 'Smooth Movement', 'Color Variation', 'Random Dot Kinematogram']

descriptions = [
    ```
            A grey dot will be at center of screen, focus your eyes on the grey dot. When a 
            green dot appears, look at the green dot directly as fast as you can, until it disappears again. 
            </br>
            </br>螢幕中央將出現一個灰點，將眼睛聚焦在灰點上。 當綠點出現時，盡可能快速地直視綠點，直到它再次消失。
            </br>.
    ```,
    ```
            When one of the green dots flashes, look at the OTHER dot that did not flash.
            </br>
            </br>螢幕中央有一個灰點，兩側各有兩個綠點。 當其中一個綠點閃爍時，請查看另一個未閃爍的點。
            </br>
            </br>.
    ```,
    ```
    
            A green dot will smoothly move around the page. Please use your eyes to follow the green dot’s movement.
            <br>
            <br>一個綠點將平滑地在頁面上移動。 請用眼睛跟隨綠點的移動。
            <br>
            </br>.
    ```,
    ```
            One dot will show on the screen, with four more surrounding it. Please click 
            on the dot that is closest in color to the center dot. Do NOT click the center dot. 
            </br>
            </br>螢幕上將顯示一個點，周圍還有四個點。 請點選顏色最接近中心點的點。 不要點擊中心點。
            </br> .
    ```,
    ```
            A circle will appear on screen with small dots moving within. Four choices will appear. Please 
            pick the choice that best describes the movement direction of the dots inside the circle. 
            </br>
            </br>螢幕上將出現一個圓圈，其中有小點在移動。 將出現四個選擇。 請選擇最能描述圓圈內點的移動方向的選項。

    ```
]

function bclick() {
    document.getElementsByClassName("tempdisplay")[0].style.display="none";
    startTests();
    if (hehe != 1) {
        resumeRecording();
    } else {
        startRecording();
    }
}

function createTest() {
    const container = document.createElement('div');
    container.className = 'tempdisplay';
    
    const heading = document.createElement('h1');
    heading.textContent = `Test ${hehe}/5: ${titles[curind]}`;
    container.appendChild(heading);
    
    const instructionPara = document.createElement('p');
    instructionPara.className = 'error';
    instructionPara.innerHTML = descriptions[curind];
    container.appendChild(instructionPara);
    
    const buttonsDiv = document.createElement('div');
    buttonsDiv.className = 'buttons';
    
    const placeholderButton = document.createElement('button');
    placeholderButton.className = 'invis';
    placeholderButton.textContent = 'This is placeholder';
    buttonsDiv.appendChild(placeholderButton);
    
    const continueButton = document.createElement('button');
    continueButton.className = 'yea';
    continueButton.textContent = 'Continue';
    continueButton.onclick = function() {
        bclick();
        startTest();
    };
    buttonsDiv.appendChild(continueButton);
    container.appendChild(buttonsDiv);
    document.body.appendChild(container);
}
function why() {
    $('.test'+ hehe).remove();
    hehe += 1;
    curind += 1;
    $("#includedContent").load("test_" + hehe + ".html");
    createTest();
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

function finishTests() {
    pauseRecording();
    textbox = document.getElementsByClassName("tempdisplay")[0];
    textbox.style.display="block";
    textbox.getElementsByClassName('error')[0].textContent = "This test has finished. Click Continue to go to the next test.";
    textbox.getElementsByClassName("yea")[0].textContent = "Continue ";
    textbox.getElementsByClassName("yea")[0].onclick = why;
}


let camera_stream = null;
let media_recorder = null;
let blobs_recorded = [];
let video = document.querySelector("#video");

function startRecording() {
    
	camera_stream = navigator.mediaDevices.getUserMedia({ video: true, audio: true });
	video.srcObject = camera_stream;

    
	media_recorder = new MediaRecorder(camera_stream, { mimeType: 'video/webm' });

    media_recorder.addEventListener('dataavailable', function(e) {
	    blobs_recorded.push(e.data);
	});

	media_recorder.addEventListener('stop', function() {
		let video_local = URL.createObjectURL(new Blob(blobs_recorded, { type: 'video/webm' }));
		download_link.href = video_local;
	});

}
function pauseRecording() {
    mediaRecorder.pause();
};

function resumeRecording() {
    mediaRecorder.resume();
};

function endRecording() {
	media_recorder.stop(); 
}


w = window.innerWidth
setInterval(() => {
    if (Math.abs(window.innerWidth - w) != 0) {
        textbox = document.getElementsByClassName("tempdisplay")[0];
        textbox.style.display="block";
        textbox.getElementsByClassName('error')[0].textContent = "Do not resize or rotate the window or device while doing tests. This will invalidate the validity of the test.\nPlease reload the webpage to continue.\n\n進行測試時請勿調整視窗或設備的大小或旋轉視窗或設備。這將使測試的有效性失效。請重新加載網頁以繼續。";
        textbox.getElementsByClassName("yea")[0].textContent = "Reload";
        textbox.getElementsByClassName("yea")[0].onclick = function() { location.reload(); };
    }
}, 1);
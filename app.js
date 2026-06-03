document.querySelectorAll('nav button').forEach(btn=>{
btn.onclick=()=>{
document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
document.getElementById(btn.dataset.tab).classList.add('active');
};
});

document.getElementById('saveSettings').onclick=()=>{
localStorage.setItem('apiUrl',document.getElementById('apiUrl').value);
alert('Saved');
};

document.getElementById('predictBtn').onclick=async()=>{
const payload={
battle_type:document.getElementById('battleType').value,
attacker:{
attack:+a_attack.value,defense:+a_defense.value,health:+a_health.value,lethality:+a_lethality.value},
defender:{
attack:+d_attack.value,defense:+d_defense.value,health:+d_health.value,lethality:+d_lethality.value}
};

const resultDiv=document.getElementById('result');
resultDiv.innerHTML='Loading...';

try{
const r=await fetch(API_BASE_URL+'/api/predict-outcome',{
method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify(payload)
});
const data=await r.json();

resultDiv.innerHTML=`
<h3>Winner: ${data.predicted_winner}</h3>
<p>Confidence: ${data.confidence ?? ''}</p>
<div>Attacker ${data.attacker_win_probability ?? 0}%</div>
<div class='bar'><div class='fill' style='width:${data.attacker_win_probability ?? 0}%'></div></div>
<div>Defender ${data.defender_win_probability ?? 0}%</div>`;
}catch(e){resultDiv.innerHTML='API Error';}
};

(async()=>{
try{
const r=await fetch(API_BASE_URL+'/api/model-accuracy');
const d=await r.json();
document.getElementById('calibrationStats').innerText=JSON.stringify(d,null,2);
new Chart(document.getElementById('accuracyChart'),{
type:'line',
data:{labels:['Current'],datasets:[{label:'Accuracy',data:[d.accuracy||0]}]}
});
}catch(e){}
})();
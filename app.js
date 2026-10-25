// Set this to your deployed backend URL, e.g. https://your-service.onrender.com
const API_BASE = "http://localhost:8000";
// Digits only, with country code. Leave blank until you add your official store number.
const STORE_WHATSAPP = "";
const CATALOG = {
  ff:{name:"Free Fire",unit:"Diamonds",items:[{amount:100,price:80},{amount:310,price:240},{amount:520,price:400},{amount:1060,price:800},{amount:2180,price:1600},{amount:5600,price:3900}]},
  pubg:{name:"PUBG Mobile",unit:"UC",items:[{amount:60,price:80},{amount:325,price:400},{amount:660,price:800},{amount:1800,price:2000},{amount:3850,price:4000},{amount:8100,price:8000}]}
};
let game="ff", selected=0;
const $=id=>document.getElementById(id);
const money=n=>"৳ "+Number(n).toLocaleString("en-US");
function render(){
  const data=CATALOG[game], box=$("packages");box.replaceChildren();
  data.items.forEach((p,i)=>{
    const b=document.createElement("button");b.type="button";b.className="package"+(i===selected?" active":"");
    const amount=document.createElement("div");amount.className="amount";amount.textContent=p.amount.toLocaleString("en-US");
    const unit=document.createElement("div");unit.className="unit";unit.textContent=data.unit;
    const price=document.createElement("div");price.className="price";price.textContent=money(p.price);
    b.append(amount,unit,price);b.onclick=()=>{selected=i;render()};box.append(b);
  });
  const p=data.items[selected];$("sumGame").textContent=data.name;$("sumPack").textContent=p.amount+" "+data.unit;$("sumPrice").textContent=money(p.price);updateInputs();
}
function updateInputs(){$("sumUid").textContent=$("player").value.trim()||"Not entered";$("sumRegion").textContent=$("region").value}
document.querySelectorAll("[data-game]").forEach(b=>b.addEventListener("click",()=>{game=b.dataset.game;selected=0;document.querySelectorAll("[data-game]").forEach(x=>x.classList.toggle("active",x===b));render()}));
$("player").addEventListener("input",updateInputs);$("region").addEventListener("change",updateInputs);$("year").textContent=new Date().getFullYear();
$("placeOrder").addEventListener("click",async()=>{
  const uid=$("player").value.trim();
  if(!/^[a-zA-Z0-9-]{5,25}$/.test(uid)){alert("Enter a player ID containing 5–25 letters, numbers or hyphens.");return}
  const p=CATALOG[game].items[selected], out=$("orderMessage");out.textContent="Submitting order request…";
  try{
    const res=await fetch(API_BASE+"/api/orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({game,player_id:uid,region:$("region").value,package_amount:p.amount,price_bdt:p.price,payment_method:$("paymentMethod").value,payment_reference:$("paymentRef").value.trim()||null})});
    const data=await res.json();if(!res.ok)throw new Error(data.detail||"Order could not be created.");
    out.textContent="Order created: "+data.order_id+". Status: "+data.status+". Save this ID to track your order.";
    $("trackId").value=data.order_id;
    if(STORE_WHATSAPP){
      const msg=`ALPHA TOP UP ORDER\nOrder: ${data.order_id}\nGame: ${CATALOG[game].name}\nPlayer ID: ${uid}\nPackage: ${p.amount} ${CATALOG[game].unit}\nDisplayed price: ${money(p.price)}\nPayment: ${$("paymentMethod").value}\nPlease confirm final price and official payment instructions.`;
      window.open("https://wa.me/"+STORE_WHATSAPP+"?text="+encodeURIComponent(msg),"_blank","noopener,noreferrer");
    }
  }catch(e){out.textContent="Could not connect to backend. Check API_BASE and make sure the backend is running. Details: "+e.message}
});
$("trackBtn").addEventListener("click",async()=>{
  const id=$("trackId").value.trim(),out=$("trackResult");if(!id){out.textContent="Enter an order ID.";return}
  out.textContent="Checking…";
  try{const r=await fetch(API_BASE+"/api/orders/"+encodeURIComponent(id));const d=await r.json();if(!r.ok)throw new Error(d.detail||"Order not found");out.textContent=JSON.stringify(d,null,2)}
  catch(e){out.textContent="Unable to retrieve order: "+e.message}
});
$("supportBtn").addEventListener("click",()=>{if(!STORE_WHATSAPP){alert("Configure STORE_WHATSAPP in frontend/app.js first.");return}window.open("https://wa.me/"+STORE_WHATSAPP,"_blank","noopener,noreferrer")});

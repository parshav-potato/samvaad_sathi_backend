import asyncio
import httpx
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api"

async def test_analysis():
    async with httpx.AsyncClient() as client:
        # Register
        print("1. Registering...")
        reg_resp = await client.post(
            f"{BASE_URL}/users",
            json={"email": f"test_analysis_{asyncio.get_event_loop().time()}@ex.com", "password": "Test@1234", "name": "Test"}
        )
        token = reg_resp.json()["authorizedUser"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✓ Registered")
        
        # Create session
        print("\n2. Creating practice session...")
        session_resp = await client.post(
            f"{BASE_URL}/v2/structure-practice/session",
            headers=headers,
            json={"track": "JavaScript Developer", "difficulty": "easy"}
        )
        session_data = session_resp.json()
        practice_id = session_data["practiceId"]
        framework = session_data["questions"][0]["framework"]
        sections = session_data["questions"][0]["sections"]
        print(f"Practice ID: {practice_id}")
        print(f"Framework: {framework}")
        print(f"Sections: {sections}")
        
        # Create audio file
        audio_path = Path("/tmp/test_audio.mp3")
        if not audio_path.exists():
            import subprocess
            subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "sine=frequency=1000:duration=2", "-f", "mp3", str(audio_path), "-y"], 
                         capture_output=True)
        
        # Submit all sections
        print(f"\n3. Submitting {len(sections)} sections...")
        for i, section in enumerate(sections):
            print(f"  Submitting {section}...")
            with open(audio_path, "rb") as f:
                submit_resp = await client.post(
                    f"{BASE_URL}/v2/structure-practice/{practice_id}/question/0/section/{section}/submit",
                    headers=headers,
                    files={"file": ("audio.mp3", f, "audio/mpeg")},
                    data={"language": "en", "time_spent_seconds": str(30 + i * 10)}
                )
            
            if submit_resp.status_code != 200:
                print(f"    ❌ Error: {submit_resp.status_code}")
                print(f"    {submit_resp.text}")
            else:
                submit_data = submit_resp.json()
                print(f"    ✓ {submit_data.get('sectionsComplete', 0)}/{submit_data.get('totalSections', 0)} complete")
            
            await asyncio.sleep(0.3)
        
        print("\n✓ All sections submitted")
        
        # Analyze
        print("\n4. Analyzing...")
        analyze_resp = await client.post(
            f"{BASE_URL}/v2/structure-practice/{practice_id}/question/0/analyze",
            headers=headers,
            json={}
        )
        
        if analyze_resp.status_code != 200:
            print(f"❌ Analysis failed: {analyze_resp.status_code}")
            print(analyze_resp.text)
        else:
            analysis = analyze_resp.json()
            print(f"\n✅ Analysis Complete!")
            print(f"Framework: {analysis['frameworkProgress']['frameworkName']}")
            print(f"Completion: {analysis['frameworkProgress']['completionPercentage']}%")
            print(f"Sections: {analysis['frameworkProgress']['sectionsComplete']}/{analysis['frameworkProgress']['totalSections']}")
            print(f"\nKey Insight: {analysis['keyInsight']}")
            print(f"\nSection Details:")
            for sec in analysis['frameworkProgress']['sections']:
                print(f"  - {sec['name']}: {sec['status']} (time: {sec['timeSpentSeconds']}s)")

if __name__ == "__main__":
    asyncio.run(test_analysis())

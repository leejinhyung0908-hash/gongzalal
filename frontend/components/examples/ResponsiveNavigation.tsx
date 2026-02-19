'use client'

/**
 * 반응형 네비게이션 컴포넌트 예시
 *
 * 데스크톱: 가로 메뉴 + 검색바
 * 모바일: 햄버거 아이콘 → Sheet 열기
 */

import { useState } from 'react'
import { Menu, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from '@/components/ui/sheet'
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
} from '@/components/ui/navigation-menu'
import { cn } from '@/lib/utils'

interface ResponsiveNavigationProps {
    className?: string
}

export function ResponsiveNavigation({ className }: ResponsiveNavigationProps) {
    const [isOpen, setIsOpen] = useState(false)

    return (
        <nav className={cn('border-b bg-background', className)}>
            <div className="container mx-auto px-4">
                {/* 데스크톱: 가로 메뉴 + 검색바 */}
                <div className="hidden md:flex items-center justify-between h-16 gap-4">
                    {/* 로고 */}
                    <div className="flex items-center gap-2">
                        <span className="text-xl font-bold">LC Chat</span>
                    </div>

                    {/* 네비게이션 메뉴 */}
                    <NavigationMenu>
                        <NavigationMenuList>
                            <NavigationMenuItem>
                                <NavigationMenuLink href="/">홈</NavigationMenuLink>
                            </NavigationMenuItem>
                            <NavigationMenuItem>
                                <NavigationMenuLink href="/chat">채팅</NavigationMenuLink>
                            </NavigationMenuItem>
                            <NavigationMenuItem>
                                <NavigationMenuTrigger>더보기</NavigationMenuTrigger>
                                <NavigationMenuContent>
                                    <NavigationMenuLink href="/about">소개</NavigationMenuLink>
                                    <NavigationMenuLink href="/settings">설정</NavigationMenuLink>
                                </NavigationMenuContent>
                            </NavigationMenuItem>
                        </NavigationMenuList>
                    </NavigationMenu>

                    {/* 검색바 */}
                    <div className="flex items-center gap-2 flex-1 max-w-md">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="search"
                                placeholder="검색..."
                                className="pl-10"
                            />
                        </div>
                    </div>
                </div>

                {/* 모바일: 햄버거 메뉴 + Sheet */}
                <div className="flex md:hidden items-center justify-between h-14">
                    <span className="text-lg font-bold">LC Chat</span>

                    <Sheet open={isOpen} onOpenChange={setIsOpen}>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon">
                                <Menu className="h-5 w-5" />
                                <span className="sr-only">메뉴 열기</span>
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="right">
                            <SheetHeader>
                                <SheetTitle>메뉴</SheetTitle>
                                <SheetDescription>
                                    네비게이션 메뉴를 선택하세요
                                </SheetDescription>
                            </SheetHeader>
                            <div className="mt-6 flex flex-col gap-4">
                                <Button variant="ghost" className="justify-start" asChild>
                                    <a href="/" onClick={() => setIsOpen(false)}>홈</a>
                                </Button>
                                <Button variant="ghost" className="justify-start" asChild>
                                    <a href="/chat" onClick={() => setIsOpen(false)}>채팅</a>
                                </Button>
                                <Button variant="ghost" className="justify-start" asChild>
                                    <a href="/about" onClick={() => setIsOpen(false)}>소개</a>
                                </Button>
                                <Button variant="ghost" className="justify-start" asChild>
                                    <a href="/settings" onClick={() => setIsOpen(false)}>설정</a>
                                </Button>
                            </div>
                            <div className="mt-6 pt-6 border-t">
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        type="search"
                                        placeholder="검색..."
                                        className="pl-10"
                                    />
                                </div>
                            </div>
                        </SheetContent>
                    </Sheet>
                </div>
            </div>
        </nav>
    )
}

